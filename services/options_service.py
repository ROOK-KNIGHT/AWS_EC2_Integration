#!/usr/bin/env python3
"""
Options Service
Handles options data fetching, Greeks calculation, and options-specific analytics
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
import requests
import json

try:
    from py_vollib.black_scholes import black_scholes
    from py_vollib.black_scholes.greeks import delta, gamma, theta, vega, rho
    from py_vollib.black_scholes.implied_volatility import implied_volatility
    VOLLIB_AVAILABLE = True
except ImportError:
    VOLLIB_AVAILABLE = False

try:
    import mibian
    MIBIAN_AVAILABLE = True
except ImportError:
    MIBIAN_AVAILABLE = False

from models.database import db, Position, MarketData
from handlers.connection_manager import ensure_valid_tokens

logger = logging.getLogger(__name__)

class OptionsService:
    """
    Service for options data and analytics
    """
    
    def __init__(self, db_session=None):
        """
        Initialize the options service
        
        Args:
            db_session: Database session (optional)
        """
        self.db_session = db_session or db.session
        self.risk_free_rate = 0.05  # Default 5% risk-free rate
    
    def fetch_options_chain(self, symbol: str, contract_type: str = 'ALL', 
                           strike_count: int = 10, include_quotes: bool = True,
                           strategy: str = 'SINGLE', interval: str = None,
                           strike: float = None, range_type: str = 'ALL',
                           from_date: str = None, to_date: str = None,
                           volatility: float = None, underlying_price: float = None,
                           interest_rate: float = None, days_to_expiration: int = None,
                           exp_month: str = 'ALL', option_type: str = 'S') -> Dict:
        """
        Fetch options chain from Schwab API
        
        Args:
            symbol: Underlying symbol
            contract_type: Type of contracts to return (CALL, PUT, ALL)
            strike_count: Number of strikes to return
            include_quotes: Include quotes for options
            strategy: Option strategy (SINGLE, ANALYTICAL, COVERED, VERTICAL, etc.)
            interval: Strike interval for spread strategy
            strike: Specific strike price
            range_type: Range of strikes (ITM, NTM, OTM, SAK, SBK, SNK, ALL)
            from_date: Start date for expiration range
            to_date: End date for expiration range
            volatility: Volatility to use in calculations
            underlying_price: Price of underlying to use in calculations
            interest_rate: Interest rate to use in calculations
            days_to_expiration: Days to expiration
            exp_month: Expiration month (JAN, FEB, ..., ALL)
            option_type: Option type (S=Standard, NS=Non-standard, ALL)
            
        Returns:
            Dictionary containing options chain data
        """
        try:
            tokens = ensure_valid_tokens()
            if not tokens:
                return {'error': 'No valid tokens available'}
            
            access_token = tokens['access_token']
            
            # Build URL and parameters
            url = f"https://api.schwabapi.com/marketdata/v1/chains"
            
            params = {
                'symbol': symbol.upper(),
                'contractType': contract_type,
                'strikeCount': strike_count,
                'includeQuotes': str(include_quotes).lower(),
                'strategy': strategy,
                'range': range_type,
                'expMonth': exp_month,
                'optionType': option_type
            }
            
            # Add optional parameters
            if interval:
                params['interval'] = interval
            if strike:
                params['strike'] = strike
            if from_date:
                params['fromDate'] = from_date
            if to_date:
                params['toDate'] = to_date
            if volatility:
                params['volatility'] = volatility
            if underlying_price:
                params['underlyingPrice'] = underlying_price
            if interest_rate:
                params['interestRate'] = interest_rate
            if days_to_expiration:
                params['daysToExpiration'] = days_to_expiration
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Process and enhance the data
                processed_data = self._process_options_chain(data)
                
                logger.info(f"Successfully fetched options chain for {symbol}")
                return processed_data
            else:
                error_msg = f"Failed to fetch options chain: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return {'error': error_msg}
                
        except Exception as e:
            error_msg = f"Error fetching options chain: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg}
    
    def _process_options_chain(self, raw_data: Dict) -> Dict:
        """
        Process raw options chain data and add calculated metrics
        
        Args:
            raw_data: Raw options chain data from API
            
        Returns:
            Processed options chain data
        """
        try:
            processed_data = raw_data.copy()
            
            # Get underlying price
            underlying_price = raw_data.get('underlyingPrice', 0)
            
            # Process call options
            if 'callExpDateMap' in raw_data:
                processed_data['callExpDateMap'] = self._process_option_contracts(
                    raw_data['callExpDateMap'], underlying_price, 'call'
                )
            
            # Process put options
            if 'putExpDateMap' in raw_data:
                processed_data['putExpDateMap'] = self._process_option_contracts(
                    raw_data['putExpDateMap'], underlying_price, 'put'
                )
            
            # Add summary statistics
            processed_data['summary'] = self._calculate_options_summary(processed_data)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing options chain: {e}")
            return raw_data
    
    def _process_option_contracts(self, exp_date_map: Dict, underlying_price: float, 
                                option_type: str) -> Dict:
        """
        Process option contracts and add calculated Greeks
        
        Args:
            exp_date_map: Expiration date map from options chain
            underlying_price: Current underlying price
            option_type: 'call' or 'put'
            
        Returns:
            Processed expiration date map
        """
        processed_map = {}
        
        for exp_date, strike_map in exp_date_map.items():
            processed_strikes = {}
            
            # Parse expiration date
            exp_date_parts = exp_date.split(':')
            if len(exp_date_parts) >= 1:
                exp_date_str = exp_date_parts[0]
                try:
                    expiration_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                    days_to_expiration = (expiration_date - date.today()).days
                except:
                    days_to_expiration = 30  # Default fallback
            else:
                days_to_expiration = 30
            
            for strike_str, contracts in strike_map.items():
                strike_price = float(strike_str)
                processed_contracts = []
                
                for contract in contracts:
                    # Add calculated Greeks and metrics
                    enhanced_contract = contract.copy()
                    
                    # Calculate Greeks if libraries are available
                    if VOLLIB_AVAILABLE and underlying_price > 0:
                        try:
                            greeks = self._calculate_greeks(
                                underlying_price, strike_price, days_to_expiration,
                                self.risk_free_rate, contract.get('volatility', 0.2),
                                option_type
                            )
                            enhanced_contract.update(greeks)
                        except Exception as e:
                            logger.debug(f"Error calculating Greeks: {e}")
                    
                    # Add additional metrics
                    enhanced_contract.update({
                        'daysToExpiration': days_to_expiration,
                        'moneyness': self._calculate_moneyness(underlying_price, strike_price, option_type),
                        'intrinsicValue': self._calculate_intrinsic_value(underlying_price, strike_price, option_type),
                        'timeValue': self._calculate_time_value(contract.get('mark', 0), underlying_price, strike_price, option_type)
                    })
                    
                    processed_contracts.append(enhanced_contract)
                
                processed_strikes[strike_str] = processed_contracts
            
            processed_map[exp_date] = processed_strikes
        
        return processed_map
    
    def _calculate_greeks(self, underlying_price: float, strike_price: float,
                         days_to_expiration: int, risk_free_rate: float,
                         implied_vol: float, option_type: str) -> Dict:
        """
        Calculate option Greeks using Black-Scholes model
        
        Args:
            underlying_price: Current price of underlying
            strike_price: Strike price of option
            days_to_expiration: Days until expiration
            risk_free_rate: Risk-free interest rate
            implied_vol: Implied volatility
            option_type: 'call' or 'put'
            
        Returns:
            Dictionary containing calculated Greeks
        """
        try:
            # Convert days to years
            time_to_expiration = days_to_expiration / 365.0
            
            if time_to_expiration <= 0:
                return {
                    'calculatedDelta': 0,
                    'calculatedGamma': 0,
                    'calculatedTheta': 0,
                    'calculatedVega': 0,
                    'calculatedRho': 0
                }
            
            # Calculate Greeks
            flag = 'c' if option_type.lower() == 'call' else 'p'
            
            calculated_delta = delta(flag, underlying_price, strike_price, 
                                   time_to_expiration, risk_free_rate, implied_vol)
            calculated_gamma = gamma(flag, underlying_price, strike_price, 
                                   time_to_expiration, risk_free_rate, implied_vol)
            calculated_theta = theta(flag, underlying_price, strike_price, 
                                   time_to_expiration, risk_free_rate, implied_vol)
            calculated_vega = vega(flag, underlying_price, strike_price, 
                                 time_to_expiration, risk_free_rate, implied_vol)
            calculated_rho = rho(flag, underlying_price, strike_price, 
                               time_to_expiration, risk_free_rate, implied_vol)
            
            return {
                'calculatedDelta': round(calculated_delta, 4),
                'calculatedGamma': round(calculated_gamma, 4),
                'calculatedTheta': round(calculated_theta, 4),
                'calculatedVega': round(calculated_vega, 4),
                'calculatedRho': round(calculated_rho, 4)
            }
            
        except Exception as e:
            logger.debug(f"Error calculating Greeks: {e}")
            return {
                'calculatedDelta': 0,
                'calculatedGamma': 0,
                'calculatedTheta': 0,
                'calculatedVega': 0,
                'calculatedRho': 0
            }
    
    def _calculate_moneyness(self, underlying_price: float, strike_price: float, 
                           option_type: str) -> str:
        """
        Calculate option moneyness (ITM, ATM, OTM)
        
        Args:
            underlying_price: Current price of underlying
            strike_price: Strike price of option
            option_type: 'call' or 'put'
            
        Returns:
            Moneyness string
        """
        if abs(underlying_price - strike_price) / underlying_price < 0.02:
            return 'ATM'  # At the money (within 2%)
        
        if option_type.lower() == 'call':
            return 'ITM' if underlying_price > strike_price else 'OTM'
        else:  # put
            return 'ITM' if underlying_price < strike_price else 'OTM'
    
    def _calculate_intrinsic_value(self, underlying_price: float, strike_price: float, 
                                 option_type: str) -> float:
        """
        Calculate intrinsic value of option
        
        Args:
            underlying_price: Current price of underlying
            strike_price: Strike price of option
            option_type: 'call' or 'put'
            
        Returns:
            Intrinsic value
        """
        if option_type.lower() == 'call':
            return max(0, underlying_price - strike_price)
        else:  # put
            return max(0, strike_price - underlying_price)
    
    def _calculate_time_value(self, option_price: float, underlying_price: float, 
                            strike_price: float, option_type: str) -> float:
        """
        Calculate time value of option
        
        Args:
            option_price: Current option price
            underlying_price: Current price of underlying
            strike_price: Strike price of option
            option_type: 'call' or 'put'
            
        Returns:
            Time value
        """
        intrinsic_value = self._calculate_intrinsic_value(underlying_price, strike_price, option_type)
        return max(0, option_price - intrinsic_value)
    
    def _calculate_options_summary(self, options_data: Dict) -> Dict:
        """
        Calculate summary statistics for options chain
        
        Args:
            options_data: Processed options chain data
            
        Returns:
            Summary statistics
        """
        try:
            summary = {
                'totalCallVolume': 0,
                'totalPutVolume': 0,
                'totalCallOpenInterest': 0,
                'totalPutOpenInterest': 0,
                'putCallRatio': 0,
                'maxPain': 0,
                'impliedVolatilityRange': {'min': float('inf'), 'max': 0},
                'mostActiveStrikes': []
            }
            
            call_volumes = []
            put_volumes = []
            call_oi = []
            put_oi = []
            iv_values = []
            strike_activity = {}
            
            # Process calls
            if 'callExpDateMap' in options_data:
                for exp_date, strikes in options_data['callExpDateMap'].items():
                    for strike, contracts in strikes.items():
                        for contract in contracts:
                            volume = contract.get('totalVolume', 0)
                            oi = contract.get('openInterest', 0)
                            iv = contract.get('volatility', 0)
                            
                            call_volumes.append(volume)
                            call_oi.append(oi)
                            if iv > 0:
                                iv_values.append(iv)
                            
                            strike_key = f"{strike}_CALL"
                            strike_activity[strike_key] = strike_activity.get(strike_key, 0) + volume
            
            # Process puts
            if 'putExpDateMap' in options_data:
                for exp_date, strikes in options_data['putExpDateMap'].items():
                    for strike, contracts in strikes.items():
                        for contract in contracts:
                            volume = contract.get('totalVolume', 0)
                            oi = contract.get('openInterest', 0)
                            iv = contract.get('volatility', 0)
                            
                            put_volumes.append(volume)
                            put_oi.append(oi)
                            if iv > 0:
                                iv_values.append(iv)
                            
                            strike_key = f"{strike}_PUT"
                            strike_activity[strike_key] = strike_activity.get(strike_key, 0) + volume
            
            # Calculate summary values
            summary['totalCallVolume'] = sum(call_volumes)
            summary['totalPutVolume'] = sum(put_volumes)
            summary['totalCallOpenInterest'] = sum(call_oi)
            summary['totalPutOpenInterest'] = sum(put_oi)
            
            if summary['totalCallVolume'] > 0:
                summary['putCallRatio'] = summary['totalPutVolume'] / summary['totalCallVolume']
            
            if iv_values:
                summary['impliedVolatilityRange'] = {
                    'min': min(iv_values),
                    'max': max(iv_values),
                    'avg': sum(iv_values) / len(iv_values)
                }
            
            # Most active strikes
            sorted_strikes = sorted(strike_activity.items(), key=lambda x: x[1], reverse=True)
            summary['mostActiveStrikes'] = sorted_strikes[:10]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error calculating options summary: {e}")
            return {}
    
    def calculate_portfolio_greeks(self) -> Dict:
        """
        Calculate aggregate Greeks for all options positions
        
        Returns:
            Dictionary containing portfolio Greeks
        """
        try:
            options_positions = self.db_session.query(Position).filter(
                Position.is_option == True,
                Position.quantity != 0
            ).all()
            
            if not options_positions:
                return {
                    'totalDelta': 0,
                    'totalGamma': 0,
                    'totalTheta': 0,
                    'totalVega': 0,
                    'netDeltaExposure': 0,
                    'thetaDecayPerDay': 0,
                    'positionCount': 0
                }
            
            total_delta = 0
            total_gamma = 0
            total_theta = 0
            total_vega = 0
            net_delta_exposure = 0
            
            for position in options_positions:
                quantity = position.quantity
                delta_val = position.delta or 0
                gamma_val = position.gamma or 0
                theta_val = position.theta or 0
                vega_val = position.vega or 0
                current_price = position.current_price or 0
                
                # Aggregate Greeks (weighted by quantity)
                total_delta += delta_val * quantity
                total_gamma += gamma_val * quantity
                total_theta += theta_val * quantity
                total_vega += vega_val * quantity
                
                # Net delta exposure in dollars
                net_delta_exposure += delta_val * quantity * 100 * current_price
            
            return {
                'totalDelta': round(total_delta, 4),
                'totalGamma': round(total_gamma, 4),
                'totalTheta': round(total_theta, 4),
                'totalVega': round(total_vega, 4),
                'netDeltaExposure': round(net_delta_exposure, 2),
                'thetaDecayPerDay': round(total_theta, 2),
                'positionCount': len(options_positions)
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio Greeks: {e}")
            return {}
    
    def get_iv_rank_percentile(self, symbol: str, current_iv: float, 
                              lookback_days: int = 252) -> Dict:
        """
        Calculate IV rank and percentile for a symbol
        
        Args:
            symbol: Stock symbol
            current_iv: Current implied volatility
            lookback_days: Number of days to look back for calculation
            
        Returns:
            Dictionary containing IV rank and percentile
        """
        try:
            # Get historical IV data from market data
            start_date = datetime.now() - timedelta(days=lookback_days)
            
            historical_iv = self.db_session.query(MarketData.implied_volatility).filter(
                MarketData.symbol == symbol,
                MarketData.timestamp >= start_date,
                MarketData.implied_volatility.isnot(None)
            ).all()
            
            if not historical_iv:
                return {'iv_rank': 0, 'iv_percentile': 0, 'error': 'No historical IV data'}
            
            iv_values = [iv[0] for iv in historical_iv]
            iv_values.sort()
            
            # Calculate IV rank (current IV relative to 52-week high/low)
            iv_min = min(iv_values)
            iv_max = max(iv_values)
            
            if iv_max > iv_min:
                iv_rank = ((current_iv - iv_min) / (iv_max - iv_min)) * 100
            else:
                iv_rank = 50
            
            # Calculate IV percentile (percentage of days current IV was higher)
            lower_count = sum(1 for iv in iv_values if iv < current_iv)
            iv_percentile = (lower_count / len(iv_values)) * 100
            
            return {
                'iv_rank': round(iv_rank, 2),
                'iv_percentile': round(iv_percentile, 2),
                'current_iv': current_iv,
                'iv_min_52w': iv_min,
                'iv_max_52w': iv_max,
                'data_points': len(iv_values)
            }
            
        except Exception as e:
            logger.error(f"Error calculating IV rank/percentile: {e}")
            return {'error': str(e)}
    
    def find_option_opportunities(self, criteria: Dict) -> List[Dict]:
        """
        Find option trading opportunities based on criteria
        
        Args:
            criteria: Dictionary containing search criteria
                     {
                         'min_iv_rank': 70,
                         'max_days_to_expiration': 45,
                         'min_volume': 100,
                         'option_type': 'put',
                         'moneyness': 'OTM'
                     }
            
        Returns:
            List of option opportunities
        """
        try:
            # This would typically involve screening multiple symbols
            # For now, return a placeholder structure
            opportunities = []
            
            # Get symbols from current positions or watchlist
            symbols = self.db_session.query(Position.symbol).distinct().all()
            
            for symbol_tuple in symbols[:5]:  # Limit to 5 symbols for demo
                symbol = symbol_tuple[0]
                
                # Fetch options chain
                options_data = self.fetch_options_chain(
                    symbol=symbol,
                    contract_type=criteria.get('option_type', 'ALL').upper(),
                    strike_count=20
                )
                
                if 'error' not in options_data:
                    # Analyze options based on criteria
                    symbol_opportunities = self._analyze_options_for_opportunities(
                        symbol, options_data, criteria
                    )
                    opportunities.extend(symbol_opportunities)
            
            # Sort by attractiveness score
            opportunities.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return opportunities[:20]  # Return top 20 opportunities
            
        except Exception as e:
            logger.error(f"Error finding option opportunities: {e}")
            return []
    
    def _analyze_options_for_opportunities(self, symbol: str, options_data: Dict, 
                                         criteria: Dict) -> List[Dict]:
        """
        Analyze options for a specific symbol to find opportunities
        
        Args:
            symbol: Stock symbol
            options_data: Options chain data
            criteria: Search criteria
            
        Returns:
            List of opportunities for this symbol
        """
        opportunities = []
        
        try:
            underlying_price = options_data.get('underlyingPrice', 0)
            
            # Analyze calls if requested
            if criteria.get('option_type', 'ALL').upper() in ['CALL', 'ALL']:
                call_opportunities = self._find_opportunities_in_contracts(
                    symbol, options_data.get('callExpDateMap', {}), 
                    underlying_price, 'call', criteria
                )
                opportunities.extend(call_opportunities)
            
            # Analyze puts if requested
            if criteria.get('option_type', 'ALL').upper() in ['PUT', 'ALL']:
                put_opportunities = self._find_opportunities_in_contracts(
                    symbol, options_data.get('putExpDateMap', {}), 
                    underlying_price, 'put', criteria
                )
                opportunities.extend(put_opportunities)
            
        except Exception as e:
            logger.error(f"Error analyzing options for {symbol}: {e}")
        
        return opportunities
    
    def _find_opportunities_in_contracts(self, symbol: str, exp_date_map: Dict,
                                       underlying_price: float, option_type: str,
                                       criteria: Dict) -> List[Dict]:
        """
        Find opportunities in option contracts
        
        Args:
            symbol: Stock symbol
            exp_date_map: Expiration date map
            underlying_price: Current underlying price
            option_type: 'call' or 'put'
            criteria: Search criteria
            
        Returns:
            List of opportunities
        """
        opportunities = []
        
        for exp_date, strikes in exp_date_map.items():
            # Parse expiration date to get days to expiration
            try:
                exp_date_str = exp_date.split(':')[0]
                expiration_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date()
                days_to_expiration = (expiration_date - date.today()).days
            except:
                continue
            
            # Filter by days to expiration
            max_dte = criteria.get('max_days_to_expiration', 365)
            if days_to_expiration > max_dte:
                continue
            
            for strike_str, contracts in strikes.items():
                strike_price = float(strike_str)
                
                for contract in contracts:
                    # Apply filters
                    volume = contract.get('totalVolume', 0)
                    min_volume = criteria.get('min_volume', 0)
                    if volume < min_volume:
                        continue
                    
                    # Check moneyness
                    moneyness = self._calculate_moneyness(underlying_price, strike_price, option_type)
                    if criteria.get('moneyness') and criteria['moneyness'].upper() != moneyness:
                        continue
                    
                    # Calculate opportunity score
                    score = self._calculate_opportunity_score(contract, criteria)
                    
                    opportunity = {
                        'symbol': symbol,
                        'option_type': option_type.upper(),
                        'strike': strike_price,
                        'expiration': exp_date_str,
                        'days_to_expiration': days_to_expiration,
                        'bid': contract.get('bid', 0),
                        'ask': contract.get('ask', 0),
                        'mark': contract.get('mark', 0),
                        'volume': volume,
                        'open_interest': contract.get('openInterest', 0),
                        'implied_volatility': contract.get('volatility', 0),
                        'delta': contract.get('delta', 0),
                        'theta': contract.get('theta', 0),
                        'moneyness': moneyness,
                        'score': score,
                        'underlying_price': underlying_price
                    }
                    
                    opportunities.append(opportunity)
        
        return opportunities
    
    def _calculate_opportunity_score(self, contract: Dict, criteria: Dict) -> float:
        """
        Calculate a score for an option opportunity
        
        Args:
            contract: Option contract data
            criteria: Search criteria
            
        Returns:
            Opportunity score (higher is better)
        """
        score = 0
        
        try:
            # Volume score (higher volume = better liquidity)
            volume = contract.get('totalVolume', 0)
            if volume > 100:
                score += min(volume / 100, 10)  # Cap at 10 points
            
            # Open interest score
            oi = contract.get('openInterest', 0)
            if oi > 100:
                score += min(oi / 100, 5)  # Cap at 5 points
            
            # Bid-ask spread score (tighter spread = better)
            bid = contract.get('bid', 0)
            ask = contract.get('ask', 0)
            if bid > 0 and ask > 0:
                spread = ask - bid
                mid_price = (bid + ask) / 2
                if mid_price > 0:
                    spread_pct = spread / mid_price
                    score += max(0, 5 - (spread_pct * 100))  # Better score for tighter spreads
            
            # IV rank bonus (if available in criteria)
            iv = contract.get('volatility', 0)
            min_iv_rank = criteria.get('min_iv_rank', 0)
            if iv > min_iv_rank / 100:
                score += 3
            
        except Exception as e:
            logger.debug(f"Error calculating opportunity score: {e}")
        
        return round(score, 2)

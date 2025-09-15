#!/bin/bash
# ==========================================================
# AWS Cleanup Script - Remove all resources created for Schwab API
# Eduardo Menck - 2025-09-06
# Updated: 2025-09-15 - Made safer and more targeted
# ==========================================================

set -e  # Exit on any error

REGION="us-east-1"
STACK_NAME="schwab-api-stack"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Safety confirmation
echo "==> AWS Cleanup Script for Schwab API Stack"
echo "    Region: $REGION"
echo "    Stack: $STACK_NAME"
echo ""
print_warning "This will delete ALL resources associated with the $STACK_NAME CloudFormation stack."
print_warning "This action cannot be undone!"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    print_error "Cleanup cancelled by user."
    exit 1
fi

echo ""
print_status "Starting AWS cleanup in region: $REGION"

# 1. Delete CloudFormation Stack
echo "[1/7] Deleting CloudFormation stack..."
aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION 2>/dev/null
aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION 2>/dev/null
echo "   ✅ CloudFormation stack removed (if existed)."

# 2. Terminate EC2 instances (only from our stack)
echo "[2/7] Terminating EC2 instances from stack..."
INSTANCE_IDS=$(aws ec2 describe-instances --region $REGION \
  --filters "Name=instance-state-name,Values=running,pending,stopping,stopped" \
  --filters "Name=tag:aws:cloudformation:stack-name,Values=$STACK_NAME" \
  --query "Reservations[].Instances[].InstanceId" --output text)
if [ -n "$INSTANCE_IDS" ]; then
  aws ec2 terminate-instances --instance-ids $INSTANCE_IDS --region $REGION
  aws ec2 wait instance-terminated --instance-ids $INSTANCE_IDS --region $REGION
  echo "   ✅ Stack instances terminated."
else
  echo "   ✅ No stack instances found."
fi

# 3. Delete Secrets Manager secrets (only our stack's secrets)
echo "[3/7] Deleting Secrets..."
SECRETS=$(aws secretsmanager list-secrets --region $REGION \
  --query "SecretList[?contains(Name, 'schwab-api') || contains(Name, 'production/schwab-api')].Name" --output text)
for SECRET in $SECRETS; do
  aws secretsmanager delete-secret --secret-id "$SECRET" --region $REGION --force-delete-without-recovery
  echo "   🔹 Deleted secret: $SECRET"
done
[ -z "$SECRETS" ] && echo "   ✅ No stack secrets found."

# 4. Delete VPC-related resources (only from our stack)
echo "[4/7] Cleaning VPCs from stack..."
VPCS=$(aws ec2 describe-vpcs --region $REGION \
  --filters "Name=tag:aws:cloudformation:stack-name,Values=$STACK_NAME" \
  --query "Vpcs[].VpcId" --output text)
for VPC in $VPCS; do
  echo "   ➡ Processing stack VPC: $VPC"

  # Delete NAT Gateways first (if any)
  NATGWS=$(aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VPC" --region $REGION --query "NatGateways[].NatGatewayId" --output text)
  for NATGW in $NATGWS; do
    aws ec2 delete-nat-gateway --nat-gateway-id $NATGW --region $REGION
    echo "     🔹 Deleted NAT Gateway: $NATGW"
  done

  # Wait for NAT Gateways to be deleted
  if [ -n "$NATGWS" ]; then
    echo "     ⏳ Waiting for NAT Gateways to be deleted..."
    sleep 30
  fi

  # Subnets
  SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC" --region $REGION --query "Subnets[].SubnetId" --output text)
  for SUBNET in $SUBNETS; do
    aws ec2 delete-subnet --subnet-id $SUBNET --region $REGION 2>/dev/null
    echo "     🔹 Deleted subnet: $SUBNET"
  done

  # Route Tables (skip main)
  RTBS=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC" --region $REGION --query "RouteTables[].RouteTableId" --output text)
  for RTB in $RTBS; do
    MAIN=$(aws ec2 describe-route-tables --route-table-ids $RTB --region $REGION --query "RouteTables[].Associations[].Main" --output text)
    if [[ "$MAIN" != "True" ]]; then
      aws ec2 delete-route-table --route-table-id $RTB --region $REGION 2>/dev/null
      echo "     🔹 Deleted route table: $RTB"
    fi
  done

  # Internet Gateways
  IGWS=$(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC" --region $REGION --query "InternetGateways[].InternetGatewayId" --output text)
  for IGW in $IGWS; do
    aws ec2 detach-internet-gateway --internet-gateway-id $IGW --vpc-id $VPC --region $REGION 2>/dev/null
    aws ec2 delete-internet-gateway --internet-gateway-id $IGW --region $REGION 2>/dev/null
    echo "     🔹 Deleted IGW: $IGW"
  done

  # Security Groups (skip default)
  SGS=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC" --region $REGION --query "SecurityGroups[].GroupId" --output text)
  for SG in $SGS; do
    DEFAULT=$(aws ec2 describe-security-groups --group-ids $SG --region $REGION --query "SecurityGroups[].GroupName" --output text)
    if [[ "$DEFAULT" != "default" ]]; then
      aws ec2 delete-security-group --group-id $SG --region $REGION 2>/dev/null
      echo "     🔹 Deleted SG: $SG"
    fi
  done

  # Finally delete VPC
  aws ec2 delete-vpc --vpc-id $VPC --region $REGION 2>/dev/null
  echo "   ✅ Deleted VPC: $VPC"
done
[ -z "$VPCS" ] && echo "   ✅ No stack VPCs found."

# 5. Delete orphaned Elastic IPs (optional)
echo "[5/7] Checking Elastic IPs..."
EIPS=$(aws ec2 describe-addresses --region $REGION --query "Addresses[].AllocationId" --output text)
for EIP in $EIPS; do
  echo "   ⚠ Elastic IP found: $EIP (not deleting because you said you want to keep it)"
done

# 6. Delete Key Pairs (optional, if you want a fresh start)
echo "[6/7] Checking Key Pairs..."
KEYS=$(aws ec2 describe-key-pairs --region $REGION --query "KeyPairs[].KeyName" --output text)
for KEY in $KEYS; do
  if [[ "$KEY" == schwab-api-keypair* ]]; then
    aws ec2 delete-key-pair --key-name $KEY --region $REGION
    echo "   🔹 Deleted key pair: $KEY"
  fi
done

# 7. Final validation
echo "[7/7] Validation..."
echo "Instances: $(aws ec2 describe-instances --region $REGION --query "Reservations[].Instances[].InstanceId" --output text)"
echo "VPCs: $(aws ec2 describe-vpcs --region $REGION --query "Vpcs[].VpcId" --output text)"
echo "Secrets: $(aws secretsmanager list-secrets --region $REGION --query "SecretList[].Name" --output text)"

echo "==> Cleanup complete ✅"

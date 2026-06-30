# --------------------------------------------------------------------------
# Environment Module – Outputs
# --------------------------------------------------------------------------

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "service_security_group_id" {
  description = "Service security group ID"
  value       = aws_security_group.service.id
}

output "nat_gateway_ip" {
  description = "NAT gateway public IP"
  value       = aws_eip.nat.public_ip
}

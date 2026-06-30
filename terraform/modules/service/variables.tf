# --------------------------------------------------------------------------
# Service Module – Variables
# --------------------------------------------------------------------------

variable "service_name" {
  description = "Name of the service"
  type        = string
}

variable "service_type" {
  description = "Type of service: web, api, or worker"
  type        = string
  validation {
    condition     = contains(["web", "api", "worker"], var.service_type)
    error_message = "service_type must be web, api, or worker."
  }
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "container_image" {
  description = "Container image URI"
  type        = string
  default     = "public.ecr.aws/nginx/nginx:latest"
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8080
}

variable "cpu" {
  description = "CPU units for Fargate task (e.g. 256, 512, 1024)"
  type        = string
  default     = "256"
}

variable "memory" {
  description = "Memory in MiB for Fargate task"
  type        = string
  default     = "512"
}

variable "desired_count" {
  description = "Desired ECS task count"
  type        = number
  default     = 1
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for ALB"
  type        = list(string)
}

variable "private_subnet_ids" {
  description = "Private subnet IDs for ECS tasks"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group for the ALB"
  type        = string
}

variable "service_security_group_id" {
  description = "Security group for the ECS tasks"
  type        = string
}

variable "health_check_path" {
  description = "ALB health check path"
  type        = string
  default     = "/health"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

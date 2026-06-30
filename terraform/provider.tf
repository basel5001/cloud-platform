# --------------------------------------------------------------------------
# Root provider configuration
# --------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "cloud-platform-tfstate"
    key            = "platform/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "cloud-platform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "cloud-platform"
      ManagedBy = "terraform"
    }
  }
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

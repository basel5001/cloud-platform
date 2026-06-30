# --------------------------------------------------------------------------
# Terraform: Service Module
# Creates ECS Fargate / Lambda + ALB + CloudWatch + IAM
# --------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# --------------------------------------------------------------------------
# Locals
# --------------------------------------------------------------------------
locals {
  name_prefix = "${var.service_name}-${var.environment}"
  common_tags = {
    Service     = var.service_name
    Environment = var.environment
    ManagedBy   = "cloud-platform"
  }
}

# --------------------------------------------------------------------------
# CloudWatch Log Group
# --------------------------------------------------------------------------
resource "aws_cloudwatch_log_group" "service" {
  name              = "/platform/${local.name_prefix}"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

# --------------------------------------------------------------------------
# IAM – Task Execution Role (ECS) / Lambda Role
# --------------------------------------------------------------------------
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = var.service_type == "worker" ? ["lambda.amazonaws.com"] : ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name_prefix}-exec"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name               = "${local.name_prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = local.common_tags
}

# --------------------------------------------------------------------------
# ALB (for web / api types only)
# --------------------------------------------------------------------------
resource "aws_lb" "service" {
  count              = var.service_type != "worker" ? 1 : 0
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [var.alb_security_group_id]
  tags               = local.common_tags
}

resource "aws_lb_target_group" "service" {
  count       = var.service_type != "worker" ? 1 : 0
  name        = "${local.name_prefix}-tg"
  port        = var.container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = var.health_check_path
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
  }
  tags = local.common_tags
}

resource "aws_lb_listener" "http" {
  count             = var.service_type != "worker" ? 1 : 0
  load_balancer_arn = aws_lb.service[0].arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.service[0].arn
  }
}

# --------------------------------------------------------------------------
# ECS Fargate (web / api)
# --------------------------------------------------------------------------
resource "aws_ecs_cluster" "service" {
  count = var.service_type != "worker" ? 1 : 0
  name  = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  tags = local.common_tags
}

resource "aws_ecs_task_definition" "service" {
  count                    = var.service_type != "worker" ? 1 : 0
  family                   = local.name_prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = var.service_name
    image     = var.container_image
    essential = true
    portMappings = [{
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.service.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
  tags = local.common_tags
}

resource "aws_ecs_service" "service" {
  count           = var.service_type != "worker" ? 1 : 0
  name            = local.name_prefix
  cluster         = aws_ecs_cluster.service[0].id
  task_definition = aws_ecs_task_definition.service[0].arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.service_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.service[0].arn
    container_name   = var.service_name
    container_port   = var.container_port
  }
  tags = local.common_tags
}

# --------------------------------------------------------------------------
# Lambda (worker type)
# --------------------------------------------------------------------------
resource "aws_lambda_function" "worker" {
  count         = var.service_type == "worker" ? 1 : 0
  function_name = local.name_prefix
  role          = aws_iam_role.execution.arn
  package_type  = "Image"
  image_uri     = var.container_image
  timeout       = 300
  memory_size   = tonumber(var.memory)

  environment {
    variables = {
      ENVIRONMENT = var.environment
    }
  }

  logging_config {
    log_group  = aws_cloudwatch_log_group.service.name
    log_format = "JSON"
  }
  tags = local.common_tags
}

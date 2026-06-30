# --------------------------------------------------------------------------
# Service Module – Outputs
# --------------------------------------------------------------------------

output "service_url" {
  description = "ALB DNS name (web/api services)"
  value       = var.service_type != "worker" ? aws_lb.service[0].dns_name : null
}

output "log_group" {
  description = "CloudWatch log group name"
  value       = aws_cloudwatch_log_group.service.name
}

output "execution_role_arn" {
  description = "IAM execution role ARN"
  value       = aws_iam_role.execution.arn
}

output "task_role_arn" {
  description = "IAM task role ARN"
  value       = aws_iam_role.task.arn
}

output "lambda_function_name" {
  description = "Lambda function name (worker services)"
  value       = var.service_type == "worker" ? aws_lambda_function.worker[0].function_name : null
}

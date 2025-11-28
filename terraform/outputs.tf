output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.app_server.id
}

output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.app_server.public_ip
}

output "app_url" {
  description = "URL to access the application"
  value       = "http://${aws_instance.app_server.public_ip}:8501"
}

output "db_endpoint" {
  description = "RDS PostgreSQL endpoint (not publicly accessible)"
  value       = aws_db_instance.finance.endpoint
}

output "db_master_username" {
  description = "Master username for the RDS instance"
  value       = aws_db_instance.finance.username
}

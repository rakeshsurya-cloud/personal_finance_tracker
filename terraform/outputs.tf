output "instance_id" {
  description = "ID of the EC2 instance"
  value       = module.compute.instance_id
}

output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = module.compute.public_ip
}

output "app_url" {
  description = "URL to access the application"
  value       = module.compute.app_url
}

output "db_endpoint" {
  description = "RDS PostgreSQL endpoint (not publicly accessible)"
  value       = module.database.db_endpoint
}

output "db_master_username" {
  description = "Master username for the RDS instance"
  value       = module.database.db_master_username
}

output "db_endpoint" {
  description = "RDS PostgreSQL endpoint (not publicly accessible)"
  value       = aws_db_instance.finance.endpoint
}

output "db_master_username" {
  description = "Master username for the RDS instance"
  value       = aws_db_instance.finance.username
}

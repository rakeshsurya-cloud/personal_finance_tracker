resource "aws_subnet" "private_a" {
  vpc_id                  = var.vpc_id
  cidr_block              = var.private_subnet_a_cidr
  availability_zone       = var.availability_zone_a
  map_public_ip_on_launch = false

  tags = {
    Name = "finance-private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id                  = var.vpc_id
  cidr_block              = var.private_subnet_b_cidr
  availability_zone       = var.availability_zone_b
  map_public_ip_on_launch = false

  tags = {
    Name = "finance-private-b"
  }
}

resource "aws_route_table" "private" {
  vpc_id = var.vpc_id
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

output "private_subnet_ids" {
  description = "IDs of private subnets for the database tier"
  value       = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

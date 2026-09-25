variable "name_prefix" {
  type = string
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "account_id" {
  type        = string
  description = "SaaS AWS account id, used to make S3 bucket names globally unique."
}

variable "tags" {
  type    = map(string)
  default = {}
}
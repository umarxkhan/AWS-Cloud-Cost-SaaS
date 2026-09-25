variable "name_prefix" {
  type = string
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "collection_schedule" {
  type    = string
  default = "cron(0 6 * * ? *)"
}

variable "users_table" {
  type = string
}

variable "tenants_table" {
  type = string
}

variable "customer_accounts_table" {
  type = string
}

variable "cost_data_table" {
  type = string
}

variable "collection_jobs_table" {
  type = string
}

variable "users_table_arn" {
  type = string
}

variable "tenants_table_arn" {
  type = string
}

variable "customer_accounts_table_arn" {
  type = string
}

variable "cost_data_table_arn" {
  type = string
}

variable "collection_jobs_table_arn" {
  type = string
}
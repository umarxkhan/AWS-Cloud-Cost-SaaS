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

variable "worker_arn" {
  type = string
}

variable "frontend_origin" {
  type    = string
  default = ""
}

variable "user_pool_id" {
  type = string
}

variable "client_id" {
  type = string
}
variable "name_prefix" {
  type        = string
  description = "Resource name prefix (e.g. saas-prod-)."
}

variable "region" {
  type    = string
  default = "eu-central-1"
}

variable "domain_prefix" {
  type        = string
  description = "Prefix for the Cognito Hosted UI domain."
  default     = "saas-cost-calculator"
}

variable "frontend_origin" {
  type        = string
  description = "Frontend origin used for Cognito OAuth callback and logout URLs."
}

variable "tags" {
  type    = map(string)
  default = {}
}
# Terraform + provider version constraints.
# The provider lock (.terraform.lock.hcl) is committed for reproducible versions.
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.20.0" # matches the committed lock (6.20.0)
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.7.0" # used by data.archive_file (Lambda packaging)
    }
  }
}
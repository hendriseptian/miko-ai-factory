# Miko AI Factory

Semi-automated production system for Miko children's short-form videos.

## Architecture

GitHub = code, Bible, schemas, prompts and QC web  
Cloudflare = orchestration/API  
AI Providers = interchangeable generation engines  
Google Drive = asset archive and generation history  
Human QC = final approval

## Current phase

Foundation V1:
- Miko master Bible
- Visual style Bible
- Story rules
- QC checklist
- JSON schemas
- Prompt library
- QC dashboard foundation
- Cloudflare Python Worker foundation

## Core rule

Miko's canonical identity must be preserved across every generation.

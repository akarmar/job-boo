#!/usr/bin/env bash
# Job Boo — narrated demo script
# Usage: ./demo.sh [fast|medium|slow]

set -euo pipefail

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; MAGENTA='\033[0;35m'
BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

# Speed control
SPEED="${DEMO_SPEED:-${1:-medium}}"
case "$SPEED" in
  fast)   TYPE_DELAY=0.01; PAUSE_SHORT=0.5; PAUSE_LONG=1 ;;
  medium) TYPE_DELAY=0.03; PAUSE_SHORT=1;   PAUSE_LONG=2 ;;
  slow)   TYPE_DELAY=0.05; PAUSE_SHORT=2;   PAUSE_LONG=3 ;;
  *)      TYPE_DELAY=0.03; PAUSE_SHORT=1;   PAUSE_LONG=2 ;;
esac

typeit() {
  local text="$1"
  for ((i=0; i<${#text}; i++)); do
    printf '%s' "${text:$i:1}"
    sleep "$TYPE_DELAY"
  done
  echo
}

pause()    { sleep "$PAUSE_SHORT"; }
longpause() { sleep "$PAUSE_LONG"; }

section() {
  echo
  echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BOLD}${CYAN}  $1${NC}"
  echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo
  longpause
}

narrator() { echo -e "${DIM}${MAGENTA}  $1${NC}"; pause; }
prompt()   { echo -e "${GREEN}\$ ${BOLD}$1${NC}"; pause; }
output()   { echo -e "  $1"; }
ok_box()   { echo -e "  ${GREEN}[OK]${NC} $1"; pause; }
warn_box() { echo -e "  ${YELLOW}[!]${NC} $1"; pause; }

# ── ACT 0: Welcome ─────────────────────────────────────────
clear
echo
echo -e "${BOLD}${CYAN}"
cat << 'BANNER'
       _       _         ____  _ _       _
      | | ___ | |__     |  _ \(_) | ___ | |_
   _  | |/ _ \| '_ \    | |_) | | |/ _ \| __|
  | |_| | (_) | |_) |   |  __/| | | (_) | |_
   \___/ \___/|_.__/    |_|   |_|_|\___/ \__|

  AI-Powered Job Search & Application Automation
BANNER
echo -e "${NC}"
echo -e "${DIM}  Speed: $SPEED | Press Ctrl+C to exit${NC}"
longpause

# ── ACT 1: The Problem ─────────────────────────────────────
section "Act 1: The Problem"

narrator "You're job hunting. It's 2025. Here's your life:"
echo
typeit "  1. Open LinkedIn. Search. Scroll. Open tab. Read JD."
typeit "  2. Open resume. Tweak for THIS job. Save as v47."
typeit "  3. Write cover letter. Pretend you love their mission."
typeit "  4. Fill form. Upload resume. Re-type everything from resume."
typeit "  5. Repeat 50-200 times."
echo
warn_box "Average time per application: 15-30 minutes"
warn_box "Applications needed for 1 offer: 100-200"
warn_box "That's 50-100 HOURS of repetitive work"
longpause

narrator "What if an AI did the boring parts?"

# ── ACT 2: The Solution ────────────────────────────────────
section "Act 2: Job Boo"

narrator "One tool. Four modes. AI-powered."
echo
echo -e "  ${BOLD}${GREEN}search${NC}  — Find matching jobs across multiple sources"
echo -e "  ${BOLD}${YELLOW}tailor${NC}  — AI-customize your resume per job listing"
echo -e "  ${BOLD}${RED}apply${NC}   — Submit applications with tailored materials"
echo -e "  ${BOLD}${CYAN}all${NC}     — Full pipeline: search -> score -> tailor -> apply"
longpause

# ── ACT 3: Setup ───────────────────────────────────────────
section "Act 3: Setup (60 seconds)"

prompt "pip install job-boo"
output "Installing job-boo and dependencies..."
ok_box "Installed"
pause

prompt "job-boo init"
narrator "Interactive wizard asks for:"
echo -e "  ${CYAN}Resume path${NC}      ~/Documents/resume.pdf"
echo -e "  ${CYAN}Job title${NC}        Senior Software Engineer"
echo -e "  ${CYAN}Location${NC}         remote"
echo -e "  ${CYAN}Sponsorship${NC}      yes/no"
echo -e "  ${CYAN}Salary range${NC}     \$150K - \$250K"
echo -e "  ${CYAN}AI provider${NC}      Claude or OpenAI (your API key)"
echo -e "  ${CYAN}Match threshold${NC}  60% (configurable)"
ok_box "Config saved to ~/.job-boo/config.yaml"
longpause

# ── ACT 4: AI Setup ────────────────────────────────────────
section "Act 4: AI Provider Setup"

prompt "job-boo setup-ai"
echo
echo -e "  Current provider:  ${CYAN}claude${NC}"
echo -e "  Current model:     ${CYAN}claude-sonnet-4-20250514${NC}"
echo -e "  API key:           ${CYAN}...abc123${NC}"
echo
narrator "Tests your connection with a real API call:"
echo -e "  ${BOLD}Testing connection...${NC}"
echo -e "  Response: ${GREEN}OK${NC}"
echo -e "  Tokens used: 12 in / 3 out"
ok_box "Connection successful!"
longpause

# ── ACT 5: Search ──────────────────────────────────────────
section "Act 5: Search & Score"

prompt "job-boo search"
echo
echo -e "  ${BOLD}Parsing resume...${NC}"
echo -e "  Found ${GREEN}24 skills${NC}: Python, Kubernetes, AWS, PostgreSQL, React..."
echo
echo -e "  ${BOLD}Searching for 'Senior Software Engineer'...${NC}"
echo -e "    Searching ${CYAN}Adzuna${NC}...         ${GREEN}38 new jobs${NC}"
echo -e "    Searching ${CYAN}The Muse${NC}...       ${GREEN}12 new jobs${NC}"
echo -e "    Searching ${CYAN}Remotive${NC}...       ${GREEN}21 new jobs${NC}"
echo
echo -e "  ${BOLD}Scoring 71 jobs...${NC}"
echo -e "    Keyword filter: ${GREEN}34${NC}/71 jobs passed (>= 20% keyword match)"
echo -e "    AI scoring 34 candidates..."
echo
echo -e "  ${BOLD}${GREEN}18 jobs above 60% threshold:${NC}"
echo
echo -e "  ${DIM}#   Score  Company              Title                        Flags${NC}"
echo -e "  1   ${GREEN}92%${NC}    Stripe               Senior Backend Engineer      ${GREEN}OK${NC}"
echo -e "  2   ${GREEN}88%${NC}    Datadog              Platform Engineer            ${GREEN}OK${NC}"
echo -e "  3   ${GREEN}85%${NC}    Vercel               Full Stack Engineer          ${GREEN}OK${NC}"
echo -e "  4   ${GREEN}81%${NC}    Cloudflare           Systems Engineer             ${GREEN}OK${NC}"
echo -e "  5   ${YELLOW}73%${NC}    Notion               Backend Engineer             ${GREEN}OK${NC}"
echo -e "  6   ${YELLOW}68%${NC}    Palantir             Software Engineer            ${RED}VISA${NC}"
echo -e "  ...  ...    ...                  ...                          ..."
longpause

# ── ACT 6: Score a specific URL ────────────────────────────
section "Act 6: Score a Specific Job URL"

prompt "job-boo search --url 'https://boards.greenhouse.io/stripe/jobs/12345'"
echo
echo -e "  ${BOLD}Parsing job URL...${NC}"
echo -e "  ${BOLD}Scoring...${NC}"
echo
echo -e "  Score: ${GREEN}92%${NC}"
echo -e "  Matched: Python, AWS, PostgreSQL, Kubernetes, CI/CD, REST APIs"
echo -e "  Missing: Scala (nice-to-have), Kafka"
echo -e "  Reasoning: Strong match. 6/8 required skills present. Transferable"
echo -e "             experience with event streaming covers Kafka gap."
longpause

# ── ACT 7: Tailor ──────────────────────────────────────────
section "Act 7: Resume Tailoring"

prompt "job-boo tailor 1"
echo
echo -e "  Tailoring resume for ${CYAN}Stripe - Senior Backend Engineer${NC}..."
echo -e "  Saved: ${GREEN}~/.job-boo/output/resume_stripe_senior_backend_engineer.txt${NC}"
echo
echo -e "  Generating cover letter..."
echo -e "  Saved: ${GREEN}~/.job-boo/output/cover_stripe_senior_backend_engineer.txt${NC}"
echo
narrator "AI rewrites your resume to:"
echo -e "  ${DIM}- Highlight Python/AWS/PostgreSQL experience first${NC}"
echo -e "  ${DIM}- Mirror keywords from Stripe's job description${NC}"
echo -e "  ${DIM}- Rewrite bullet points with Stripe-relevant metrics${NC}"
echo -e "  ${DIM}- Add a targeted professional summary${NC}"
echo -e "  ${DIM}* All facts stay accurate. Only ordering and emphasis change.${NC}"
longpause

# ── ACT 8: Apply ───────────────────────────────────────────
section "Act 8: Apply"

prompt "job-boo apply 1"
echo
echo -e "  ┌─────────────────────────────────────────────────┐"
echo -e "  │ ${BOLD}Senior Backend Engineer${NC} at ${CYAN}Stripe${NC}                │"
echo -e "  │ Location: Remote (US)                           │"
echo -e "  │ Score: ${GREEN}92%${NC}                                      │"
echo -e "  │ Matched: Python, AWS, PostgreSQL, K8s, CI/CD    │"
echo -e "  │ Resume: ~/.job-boo/output/resume_stripe_...   │"
echo -e "  │ Cover:  ~/.job-boo/output/cover_stripe_...    │"
echo -e "  └─────────────────────────────────────────────────┘"
echo
echo -e "  Open in browser and mark as applied? ${GREEN}[Y/n]${NC} y"
ok_box "Opened in browser."
echo -e "  Apply using the tailored resume and cover letter saved in your output directory."
longpause

# ── ACT 9: Full Pipeline ──────────────────────────────────
section "Act 9: The Full Pipeline"

prompt "job-boo all --threshold 70"
echo
echo -e "  ${BOLD}Step 1/4: Parsing resume...${NC}"
echo -e "  ${BOLD}Step 2/4: Searching...${NC}           71 jobs found"
echo -e "  ${BOLD}Step 3/4: Scoring...${NC}             18 above 70%"
echo -e "  ${BOLD}Step 4/4: Tailoring top 10...${NC}    10 resumes generated"
echo
echo -e "  Ready to apply to 18 jobs? ${GREEN}[Y/n]${NC}"
narrator "Opens each job URL in your browser, one by one, with confirmation."
longpause

# ── ACT 10: Management ────────────────────────────────────
section "Act 10: Track Everything"

prompt "job-boo status"
echo
echo -e "  ${BOLD}Pipeline Dashboard${NC}"
echo -e "  ┌──────────┬───────┐"
echo -e "  │ State    │ Count │"
echo -e "  ├──────────┼───────┤"
echo -e "  │ FOUND    │    71 │"
echo -e "  │ SCORED   │    34 │"
echo -e "  │ TAILORED │    10 │"
echo -e "  │ APPLIED  │     8 │"
echo -e "  │ SKIPPED  │     2 │"
echo -e "  │ ${BOLD}TOTAL${NC}    │  ${BOLD}71${NC} │"
echo -e "  └──────────┴───────┘"
pause

prompt "job-boo export --format csv"
output "Exported 71 jobs to ~/.job-boo/output/jobs_export.csv"
pause

prompt "job-boo doctor"
echo -e "  Config file:       ${GREEN}OK${NC}"
echo -e "  Resume PDF:        ${GREEN}OK${NC} (142 KB)"
echo -e "  AI provider:       ${GREEN}claude${NC} (model: claude-sonnet-4-20250514)"
echo -e "  AI key:            ${GREEN}...abc123${NC}"
echo -e "  Job sources:       ${GREEN}Adzuna, The Muse, Remotive${NC}"
echo -e "  Job title:         ${GREEN}Senior Software Engineer${NC}"
echo -e "  Database:          ${GREEN}71 jobs tracked${NC}"
echo
ok_box "All good!"
longpause

# ── ACT 11: Architecture ──────────────────────────────────
section "Act 11: How It Works"

narrator "Two-pass scoring saves API tokens:"
echo
echo -e "  ${DIM}Pass 1: Keyword overlap (free, instant)${NC}"
echo -e "  ${DIM}  71 jobs  ──>  34 candidates (>20% keyword match)${NC}"
echo
echo -e "  ${DIM}Pass 2: AI semantic scoring (costs tokens, accurate)${NC}"
echo -e "  ${DIM}  34 candidates  ──>  18 matches (>60% AI score)${NC}"
echo
echo -e "  ${DIM}Result: Only 34 AI calls instead of 71. ~50% token savings.${NC}"
longpause

narrator "Sponsorship detection:"
echo
echo -e "  ${DIM}Scans job descriptions for phrases like:${NC}"
echo -e "  ${RED}  'unable to sponsor' 'no visa sponsorship' 'must be authorized'${NC}"
echo -e "  ${DIM}Flags mismatches so you don't waste applications.${NC}"
longpause

# ── ACT 12: Summary ───────────────────────────────────────
section "Summary"

echo -e "  ${BOLD}${GREEN}Job Boo turns 50+ hours of manual applying into:"
echo
echo -e "  ${CYAN}  1 command${NC}  to search across multiple job boards"
echo -e "  ${CYAN}  AI scores${NC} every job against your actual skills"
echo -e "  ${CYAN}  Custom resume${NC} generated for each application"
echo -e "  ${CYAN}  Cover letter${NC} written to match the job description"
echo -e "  ${CYAN}  1 click${NC}    to apply with your tailored materials"
echo
echo -e "  ${BOLD}Get started:${NC}"
echo -e "    pip install job-boo"
echo -e "    job-boo init"
echo -e "    job-boo search"
echo
echo -e "${DIM}  github.com/akarmar/job-boo${NC}"
echo
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

#!/usr/bin/env bash
# Demo script for the Faro recognition flow. Designed to be recorded
# with asciinema and played back at human-readable pace.

set -e

GREEN='\033[1;32m'
CYAN='\033[1;36m'
YELLOW='\033[1;33m'
DIM='\033[2m'
NC='\033[0m'

step() {
  echo
  echo -e "${CYAN}━━ $1 ━━${NC}"
  sleep 1.2
}

note() {
  echo -e "${YELLOW}# $1${NC}"
  sleep 0.6
}

cmd() {
  echo -e "${DIM}\$${NC} $1"
  sleep 0.6
  eval "$1"
  sleep 1.8
}

clear

echo -e "${GREEN}╭──────────────────────────────────────────────────────╮${NC}"
echo -e "${GREEN}│  Faro — demo: enrollment and face recognition flow   │${NC}"
echo -e "${GREEN}╰──────────────────────────────────────────────────────╯${NC}"
sleep 2

step "1. The store starts empty"
cmd "curl -s http://127.0.0.1:8765/v1/persons | jq"

step "2. Try recognizing Rodolfo BEFORE enrolling him"
note "expect: no match, 'No reconozco a esta persona.'"
cmd "curl -s -X POST http://127.0.0.1:8765/v1/recognize -F 'language=es' -F 'image=@test_data/yo3.jpg' | jq '{match, spoken}'"

step "3. Enroll Rodolfo using yo3.jpg"
cmd "curl -s -X POST http://127.0.0.1:8765/v1/persons -F 'name=Rodolfo Campos' -F 'description=tu hijo mayor' -F 'image=@test_data/yo3.jpg' | jq '{id, name, description}'"

step "4. Recognize again with the SAME photo"
note "expect: high similarity, LLM-phrased Spanish cue"
cmd "curl -s -X POST http://127.0.0.1:8765/v1/recognize -F 'language=es' -F 'image=@test_data/yo3.jpg' | jq '{spoken, similarity: .match.similarity}'"

step "5. Try a DIFFERENT photo of the same person (yo.jpg)"
note "the real test — different angle, different year"
cmd "curl -s -X POST http://127.0.0.1:8765/v1/recognize -F 'language=es' -F 'image=@test_data/yo.jpg' | jq '{spoken, similarity: .match.similarity}'"

echo
echo -e "${GREEN}✓ done${NC}"
sleep 2

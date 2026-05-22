name: Require Linked Issue

on:
  pull_request:
    types: [opened, edited, reopened, synchronize]
    branches:
      - develop

jobs:
  check-linked-issue:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read

    steps:
      - name: Validar nombre de rama
        env:
          HEAD_REF: ${{ github.head_ref }}
        run: |
          VALID_PREFIXES="fix/ feat/ feature/ chore/ docs/ style/ refactor/ perf/ test/ build/ ci/ revert/"

          IS_VALID=false
          for PREFIX in $VALID_PREFIXES; do
            if [[ "$HEAD_REF" == "$PREFIX"* ]]; then
              IS_VALID=true
              break
            fi
          done

          if [ "$IS_VALID" = false ]; then
            echo "❌ Rama inválida: '$HEAD_REF'"
            echo "Las ramas deben usar prefijo: fix/, feat/, chore/, docs/, etc."
            exit 1
          fi

          echo "✅ Prefijo de rama válido."

      - name: Verificar issue vinculada
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
          REPO: ${{ github.repository }}
        run: |
          LINKED=$(gh pr view $PR_NUMBER \
            --repo $REPO \
            --json closingIssuesReferences \
            --jq '.closingIssuesReferences | length')

          echo "Issues vinculadas: $LINKED"

          if [ "$LINKED" -eq 0 ]; then
            echo "❌ Este PR no tiene ninguna issue vinculada."
            echo "Vincula una issue en la descripción con:"
            echo "  Closes #123  |  Fixes #123  |  Resolves #123"
            exit 1
          fi

          echo "✅ Issue vinculada correctamente."

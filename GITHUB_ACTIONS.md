# GitHub Actions Integration Guide

This guide explains how to run the WorkUA bot in GitHub Actions using environment variables.

## Overview

The bot now supports loading configuration from environment variables, making it perfect for CI/CD environments like GitHub Actions. No files are required - everything can be configured through environment variables.

## Key Features for CI/CD

1. **Filter from Environment Variable**: Use `FILTER_CONTENT` instead of `FILTER_PATH`
2. **Cookies from Environment Variable**: Use `WORKUA_COOKIES` instead of cookies.json file
3. **Strict Validation**: No fallbacks - missing configuration raises clear errors
4. **Headless Mode**: Perfect for running in containerized environments

## Required Environment Variables

### Authentication (choose one)
- `WORKUA_COOKIES`: JSON string of cookies from authenticated session
  ```json
  [{"name":"sessionid","value":"xxx","domain":".work.ua","path":"/","secure":true,"httpOnly":true}]
  ```
- `WORKUA_PHONE`: Phone number for SMS-based login (format: +380XXXXXXXXX)
  - **Note**: Phone login requires manual SMS code entry, so use cookies for automated runs

### Search Configuration
- `SEARCH_KEYWORDS`: Comma-separated keywords (e.g., "python developer,backend")
- `LOCATIONS`: Comma-separated cities (e.g., "Київ,Львів") - optional if REMOTE_ONLY=true

### Filter Configuration (when using LLM features)
Choose one:
- `FILTER_CONTENT`: Filter text directly in environment variable
  ```
  FILTER_CONTENT="Я шукаю вакансії Python Developer. Мінімальна зарплата: 50000 грн."
  ```
- `FILTER_PATH`: Path to filter file (e.g., "./my_filter.txt")

### LLM Configuration (when using LLM features)
- `OPENAI_API_KEY`: Your OpenAI API key
- `USE_LLM`: Set to "true" to enable LLM analysis
- `USE_PRE_APPLY_LLM_CHECK`: Set to "true" for pre-apply filtering

## Optional Environment Variables
- `MAX_APPLICATIONS`: Maximum number of applications (default: 10)
- `MIN_MATCH_PROBABILITY`: Minimum match probability % (default: 90)
- `HEADLESS`: Run browser in headless mode (default: false)
- `REMOTE_ONLY`: Only search remote jobs (default: false)
- `MODEL_NAME`: OpenAI model to use (default: gpt-4o)

## Getting Cookies for WORKUA_COOKIES

### Method 1: Browser DevTools
1. Log in to work.ua in your browser
2. Open DevTools (F12)
3. Go to Application (Chrome) or Storage (Firefox) tab
4. Click on Cookies > https://www.work.ua
5. Copy all cookies as JSON array
6. Format as: `[{"name":"cookie1","value":"xxx",...}, {"name":"cookie2",...}]`

### Method 2: Using the bot locally
1. Run the bot locally with `WORKUA_PHONE` set
2. Complete the SMS authentication
3. The bot saves cookies to `cookies.json`
4. Copy the content of `cookies.json` to `WORKUA_COOKIES` secret

### Cookie Format Example
```json
[
  {
    "name": "sessionid",
    "value": "your_session_id_here",
    "domain": ".work.ua",
    "path": "/",
    "secure": true,
    "httpOnly": true,
    "sameSite": "Lax"
  }
]
```

## GitHub Actions Setup

### 1. Add Secrets
Go to your repository: Settings > Secrets and variables > Actions

Add these secrets:
- `OPENAI_API_KEY`: Your OpenAI API key
- `WORKUA_COOKIES`: JSON string of cookies (from browser or cookies.json)

### 2. Create Workflow File
See `.github/workflows/workua-bot-example.yml` for a complete example.

### 3. Configure the Workflow
Edit the workflow file to set your preferences:
- Schedule (cron)
- Search keywords
- Locations
- Filter content
- Max applications

## Example: Minimal Configuration

```yaml
env:
  WORKUA_COOKIES: ${{ secrets.WORKUA_COOKIES }}
  SEARCH_KEYWORDS: "python developer"
  FILTER_CONTENT: "Я шукаю Python розробника з зарплатою від 40000 грн."
```

## Example: Full Configuration with LLM

```yaml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  WORKUA_COOKIES: ${{ secrets.WORKUA_COOKIES }}
  SEARCH_KEYWORDS: "python developer,backend developer"
  LOCATIONS: "Київ,Львів,Одеса"
  FILTER_CONTENT: |
    Я шукаю вакансії Python/Backend розробника.
    Досвід: від 3 років.
    Мінімальна зарплата: 50000 гривень.
    Stack: Python, Django/FastAPI, PostgreSQL, Docker.
    Вакансії від ФОП - не влаштовують.
  USE_LLM: true
  USE_PRE_APPLY_LLM_CHECK: true
  MIN_MATCH_PROBABILITY: 85
  MAX_APPLICATIONS: 15
  HEADLESS: true
```

## Validation and Error Handling

The bot now uses strict validation:

### Missing Required Fields
If required fields are missing, you'll get a clear error:
```
Configuration errors:
  - WORKUA_PHONE or WORKUA_COOKIES is required
  - SEARCH_KEYWORDS is required
```

### LLM Features Enabled
When `USE_LLM=true` or `USE_PRE_APPLY_LLM_CHECK=true`:
```
Configuration errors:
  - OPENAI_API_KEY is required when USE_LLM or USE_PRE_APPLY_LLM_CHECK is enabled
  - FILTER_PATH or FILTER_CONTENT is required when USE_LLM or USE_PRE_APPLY_LLM_CHECK is enabled
```

### Filter File Not Found
If using `FILTER_PATH` and file doesn't exist:
```
FileNotFoundError: Filter file not found: ./my_filter.txt. 
Please provide FILTER_CONTENT environment variable or create the filter file.
```

## Testing Locally with Environment Variables

You can test the same configuration locally:

```bash
# Create .env file
cat > .env << 'EOF'
WORKUA_COOKIES='[{"name":"sessionid","value":"xxx","domain":".work.ua"}]'
SEARCH_KEYWORDS=python developer
FILTER_CONTENT=Я шукаю Python розробника
USE_LLM=true
OPENAI_API_KEY=sk-xxx
HEADLESS=true
EOF

# Run the bot
python3 bot.py
```

## Troubleshooting

### Cookies Expired
If cookies expire, you'll see authentication errors. Solutions:
1. Re-authenticate in browser and get fresh cookies
2. Use `WORKUA_PHONE` for initial setup (requires manual SMS code)

### Invalid JSON in WORKUA_COOKIES
Ensure the JSON is properly formatted:
- Use double quotes for strings
- Escape special characters
- Validate with: `echo $WORKUA_COOKIES | python3 -m json.tool`

### Filter Not Loaded
Check:
1. Either `FILTER_CONTENT` or `FILTER_PATH` is set
2. If using `FILTER_PATH`, file exists
3. If using `FILTER_CONTENT`, value is not empty

## Best Practices

1. **Use WORKUA_COOKIES for automation**: Phone login requires manual intervention
2. **Refresh cookies regularly**: Set up a manual workflow to update cookies
3. **Use FILTER_CONTENT for simple filters**: Easier to maintain in GitHub Secrets
4. **Use FILTER_PATH for complex filters**: Commit filter file to repository
5. **Enable HEADLESS in CI**: Saves resources and runs faster
6. **Set appropriate MAX_APPLICATIONS**: Start small to test
7. **Monitor API usage**: OpenAI API costs money
8. **Use secrets for sensitive data**: Never commit API keys or cookies

## Security Notes

⚠️ **Never commit secrets to the repository**
- Use GitHub Secrets for sensitive data
- Don't print secrets in logs
- Rotate API keys regularly
- Cookies contain session data - treat them as passwords

## Migration from File-Based Config

### Old Way (file-based)
```bash
# .env
FILTER_PATH=./my_filter.txt

# Load cookies from file
# cookies.json exists in repository
```

### New Way (environment variables)
```bash
# .env or GitHub Secrets
FILTER_CONTENT='My filter text here'
WORKUA_COOKIES='[{cookie json here}]'
```

Both methods still work, but environment variables are recommended for CI/CD.

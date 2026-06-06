import os
import re
import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

CBS_BASE = "https://www.cbssports.com"
CBS_FANTASY_URL = f"{CBS_BASE}/fantasy/baseball/"

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
ANALYST_PROMPT = (
    "You are a fantasy baseball analyst. Based on this waiver wire column, "
    "give me the top 3 players to add and top 2 to drop for a 12-team rotisserie league. "
    "Be concise — fit the entire response under 1500 characters so it fits in a text message. "
    "Use short player names and abbreviations where possible."
)

SMS_MAX_CHARS = 1600


def find_waiver_wire_article_url() -> str | None:
    resp = requests.get(CBS_FANTASY_URL, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "waiver-wire" in href and "baseball" in href:
            if href.startswith("http"):
                return href
            return f"{CBS_BASE}{href}"
    return None


def extract_waiver_sections(article_url: str) -> str:
    resp = requests.get(article_url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    article_body = (
        soup.find("div", class_=re.compile(r"article-body|ArticleBody|article__body", re.I))
        or soup.find("article")
        or soup.find("main")
    )
    if not article_body:
        article_body = soup

    # Preferred: specific named sections
    target_phrases = [
        "thursday's top waiver",
        "wednesday's standouts",
        "top waiver-wire targets",
        "top waiver wire targets",
        "saturday's top waiver",
        "friday's top waiver",
        "this week's top waiver",
        "waiver wire targets",
        "players to add",
        "streamers",
    ]

    sections = []
    elements = article_body.find_all(["h2", "h3", "h4", "p", "ul", "ol"])

    capturing = False
    captured_count = 0

    for elem in elements:
        text_lower = elem.get_text(strip=True).lower()

        if any(phrase in text_lower for phrase in target_phrases):
            capturing = True
            captured_count = 0
            sections.append(f"\n## {elem.get_text(strip=True)}\n")
            continue

        if capturing:
            if elem.name in ("h2", "h3") and not any(phrase in text_lower for phrase in target_phrases):
                if captured_count > 2:
                    capturing = False
                    continue

            content = elem.get_text(separator=" ", strip=True)
            if content:
                sections.append(content)
                captured_count += 1

    if sections:
        return "\n".join(sections).strip()

    # Fallback: return the full article text (first 4000 chars) so Claude
    # can still extract useful info even if no section headers matched.
    print("No target sections found — falling back to full article text.")
    all_text = article_body.get_text(separator="\n", strip=True)
    return all_text[:4000]


def call_anthropic(content: str) -> str:
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"{ANALYST_PROMPT}\n\n---\n\n{content}",
            }
        ],
    )
    return message.content[0].text


def truncate_to_sms(text: str, max_chars: int = SMS_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    last_sentence_end = max(
        truncated.rfind(". "),
        truncated.rfind("! "),
        truncated.rfind("? "),
    )
    if last_sentence_end > max_chars // 2:
        return truncated[: last_sentence_end + 1].strip()
    return truncated.rstrip() + "…"


def send_sms(body: str) -> None:
    client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    client.messages.create(
        body=body,
        from_=os.environ["TWILIO_FROM_NUMBER"],
        to=os.environ["TO_PHONE_NUMBER"],
    )


def main() -> None:
    print("Looking for waiver wire article...")

    article_url = find_waiver_wire_article_url()
    if not article_url:
        fallback = (
            "Waiver wire column not found yet, check CBS Sports manually: "
            "https://www.cbssports.com/fantasy/baseball/"
        )
        send_sms(fallback)
        print("Article not found. Sent fallback SMS.")
        return

    print(f"Found article: {article_url}")

    content = extract_waiver_sections(article_url)
    if not content:
        fallback = f"Waiver wire article found but couldn't extract sections. Read it here: {article_url}"
        send_sms(fallback)
        print("Could not extract sections. Sent fallback SMS.")
        return

    print(f"Extracted {len(content)} characters of content.")

    ai_response = call_anthropic(content)
    print(f"Got AI response ({len(ai_response)} chars).")

    sms_body = truncate_to_sms(f"⚾ Fantasy Waiver Wire:\n\n{ai_response}")
    send_sms(sms_body)
    print("SMS sent successfully.")


if __name__ == "__main__":
    main()

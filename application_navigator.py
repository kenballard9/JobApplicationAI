import re
import time

from field_detector import detect_fields
from form_filler import identify_field


APPLY_PATTERN = re.compile(
    r"\bapply\b",
    re.IGNORECASE
)

EXCLUDED_PATTERN = re.compile(
    r"\b(filters?|coupon|discount|promo|"
    r"settings|changes|search|submit)\b|"
    r"\bhow to apply\b",
    re.IGNORECASE
)


def find_application_fields(page):
    best_fields = []
    best_score = 0

    for frame in page.frames:
        try:
            fields = detect_fields(frame)

            matched_keys = {
                identify_field(item["metadata"])
                for item in fields
            }

            matched_keys.discard(None)

            score = len(matched_keys)

            if score >= 2 and score > best_score:
                best_fields = fields
                best_score = score

        except Exception as error:
            print(f"Frame detection error: {error}")

    return best_fields


def wait_for_application(context, timeout=15):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        for page in reversed(context.pages):
            if page.is_closed():
                continue

            fields = find_application_fields(page)

            if fields:
                return page, fields

        time.sleep(0.5)

    return None, []


def find_apply_buttons(page):
    candidates = []

    selectors = (
        "button, "
        "a, "
        "[role='button'], "
        "[role='link'], "
        "input[type='button']"
    )

    for frame in page.frames:
        elements = frame.locator(selectors)

        for index in range(elements.count()):
            element = elements.nth(index)

            try:
                if not element.is_visible():
                    continue

                if not element.is_enabled():
                    continue

                metadata = element.evaluate("""
                    el => ({
                        text: (
                            el.innerText ||
                            el.value ||
                            el.getAttribute('aria-label') ||
                            el.getAttribute('title') ||
                            ''
                        ).trim(),
                        type: el.type || '',
                        insideForm: !!el.closest('form')
                    })
                """)

                text = metadata["text"]

                if not APPLY_PATTERN.search(text):
                    continue

                if EXCLUDED_PATTERN.search(text):
                    continue

                if metadata["type"] == "submit":
                    continue

                if metadata["insideForm"]:
                    continue

                score = 10

                if text.lower() == "apply":
                    score += 100

                if text.lower() == "apply now":
                    score += 90

                if "apply for" in text.lower():
                    score += 80

                if "apply with" in text.lower():
                    score -= 20

                candidates.append({
                    "element": element,
                    "text": text,
                    "score": score
                })

                print(f"Found Apply control: {text}")

            except Exception as error:
                print(f"Control detection error: {error}")

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return candidates


def open_application(page):
    context = page.context

    print("\nStarting application navigation...")

    if page.url.startswith("file:"):
        print("Local test application detected.")

        fields = find_application_fields(page)

        return page, fields

    try:
        page.wait_for_load_state(
            "domcontentloaded"
        )

        page.wait_for_timeout(2000)

    except Exception as error:
        print(f"Page loading warning: {error}")

    print("\nSearching for Apply buttons...")

    candidates = find_apply_buttons(page)

    print(
        f"Apply controls detected: {len(candidates)}"
    )

    if candidates:
        best_score = candidates[0]["score"]

        best_candidates = [
            item for item in candidates
            if item["score"] == best_score
        ]

        if len(best_candidates) == 1:
            candidate = best_candidates[0]

            try:
                print(
                    f"Clicking: {candidate['text']}"
                )

                candidate[
                    "element"
                ].scroll_into_view_if_needed(
                    timeout=5000
                )

                candidate["element"].click(
                    timeout=10000
                )

                print("Apply button clicked.")
                print("Waiting for application form...")

                active_page, fields = wait_for_application(
                    context,
                    timeout=15
                )

                if fields:
                    print("Application form located.")

                    return active_page, fields

            except Exception as error:
                print(f"Apply click error: {error}")

        else:
            print(
                "Multiple equally ranked Apply controls."
            )

            print(
                "Unable to safely select a unique control."
            )

            return None, []

    else:
        print("No Apply button found.")

    print("\nChecking for existing application fields...")

    active_page, fields = wait_for_application(
        context,
        timeout=10
    )

    if fields:
        print("Existing application form found.")

        return active_page, fields

    print("Unable to locate an application form.")

    return None, []

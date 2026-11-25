import json

from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

from application_navigator import open_application
from form_filler import fill_fields


BASE_DIR = Path(__file__).resolve().parent

TRUSTED_DOMAINS = [
    "job-boards.greenhouse.io",
    "boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.ashbyhq.com"
]


def is_trusted_url(url):
    parsed = urlparse(url)

    if parsed.scheme != "https":
        return False

    if parsed.username or parsed.password:
        return False

    return parsed.hostname in TRUSTED_DOMAINS


def load_profile():
    profile_path = (
        BASE_DIR / "config" / "applicant_profile.json"
    )

    with open(
        profile_path,
        "r",
        encoding="utf-8"
    ) as file:
        profile = json.load(file)

    resume_path = Path(profile["resume_path"])

    if not resume_path.is_absolute():
        resume_path = BASE_DIR / resume_path

    profile["resume_path"] = str(
        resume_path.resolve()
    )

    return profile


def get_application_url():
    print("\nSelect an application mode:")
    print("1. Local test application")
    print("2. Real application website")

    choice = input(
        "\nEnter your selection: "
    ).strip()

    if choice == "1":
        test_page = (
            BASE_DIR / "test_application.html"
        )

        if not test_page.is_file():
            raise FileNotFoundError(
                "Test application page not found."
            )

        return test_page.as_uri()

    elif choice == "2":
        url = input(
            "\nEnter application URL: "
        ).strip()

        parsed_url = urlparse(url)

        if (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
        ):
            raise ValueError(
                "Enter a valid HTTPS URL."
            )

        if not is_trusted_url(url):
            raise ValueError(
                "Application domain is not trusted."
            )

        return url

    else:
        raise ValueError("Invalid selection.")


def main():
    print("=" * 50)
    print("Job Application AI")
    print("Automatic Application Mode")
    print("=" * 50)

    try:
        profile = load_profile()
        application_url = get_application_url()

    except Exception as error:
        print(f"Configuration error: {error}")
        return

    if not Path(profile["resume_path"]).is_file():
        print("ERROR: Resume file not found.")
        return

    local_test = application_url.startswith("file:")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=False,
            slow_mo=200
        )

        try:
            page = browser.new_page()

            print("\nOpening job posting...")

            page.goto(
                application_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            print(f"Website: {page.title()}")
            print(f"URL: {page.url}")

            if not local_test:
                if not is_trusted_url(page.url):
                    print("Untrusted destination. Stopping.")
                    return

            print("\nStarting automatic navigation...")

            active_page, detected_fields = (
                open_application(page)
            )

            if active_page is None:
                print("Application form not found.")
                return

            if not detected_fields:
                print("No application fields detected.")
                return

            print(f"\nApplication URL: {active_page.url}")

            if not local_test:
                if not is_trusted_url(active_page.url):
                    print("Untrusted destination. Stopping.")
                    return

                verified_fields = []

                for item in detected_fields:
                    frame_url = item["element"].evaluate(
                        "el => el.ownerDocument.location.href"
                    )

                    if is_trusted_url(frame_url):
                        verified_fields.append(item)

                detected_fields = verified_fields

            print("\nDetecting application fields...")

            print(
                f"Detected {len(detected_fields)} fields."
            )

            print("\nAutomatically filling fields...\n")

            filled, skipped = fill_fields(
                detected_fields,
                profile
            )

            print("\n" + "=" * 50)
            print("APPLICATION SUMMARY")
            print("=" * 50)

            print(
                f"Fields detected: {len(detected_fields)}"
            )

            print(f"Fields filled:   {filled}")
            print(f"Fields skipped:  {skipped}")

            print("=" * 50)

            print("\nAutomatic form filling complete.")
            print("Application has not been submitted.")

            input("\nPress Enter to close the browser and terminate the program...")

        except Exception as error:
            print(f"Application error: {error}")

        finally:
            browser.close()


if __name__ == "__main__":
    main()

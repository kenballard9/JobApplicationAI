import re
from pathlib import Path


FIELD_ALIASES = {
    "first_name": [
        "first name",
        "given name",
        "fname",
        "preferred first name"
    ],
    "last_name": [
        "last name",
        "surname",
        "family name",
        "lname"
    ],
    "email": [
        "email",
        "email address",
        "contact email"
    ],
    "phone": [
        "phone",
        "phone number",
        "mobile",
        "telephone"
    ],
    "address": [
        "street address",
        "address line 1"
    ],
    "city": [
        "city",
        "location city",
        "location (city)",
        "city of residence"
    ],
    "state": [
        "state",
        "province",
        "location state"
    ],
    "zip_code": [
        "zip",
        "zip code",
        "postal",
        "postal code"
    ],
    "country": [
        "country"
    ],
    "education": [
        "education",
        "highest education",
        "degree"
    ],
    "field_of_study": [
        "field of study",
        "major"
    ],
    "university": [
        "university",
        "college",
        "school name"
    ],
    "desired_salary": [
        "desired salary",
        "expected salary",
        "salary expectation",
        "compensation"
    ],
    "resume_path": [
        "resume",
        "upload resume",
        "cv",
        "upload cv",
        "resume cv",
        "resume/cv",
        "attach resume",
        "attach cv"
    ]
}


def normalize(text):

    text = re.sub(
        r"([a-z])([A-Z])",
        r"\1 \2",
        str(text)
    )

    text = re.sub(
        r"[^a-zA-Z0-9]+",
        " ",
        text
    )

    return text.lower().strip()


def identify_field(metadata):

    # Get the actual field label.
    # Convert to lowercase for case-insensitive matching.

    label = str(
        metadata.get("label") or ""
    ).lower()

    field_type = metadata.get("type", "")
    field_tag = metadata.get("tag", "")

    # Determine whether the field is a text box.

    is_text_box = (
        field_type in ["text", "url", "textarea"]
        or field_tag == "textarea"
    )

    # LinkedIn and GitHub must match the actual label.
    # Do not use any other metadata for these fields.

    has_linkedin = "linkedin" in label
    has_github = "github" in label

    if has_linkedin or has_github:

        if not is_text_box:
            return None

        # Skip ambiguous labels containing both names.

        if has_linkedin and has_github:
            return None

        if has_linkedin:
            return "linkedin"

        if has_github:
            return "github"

    # Standard matching for all other fields.

    search_keys = [
        "label",
        "aria_label",
        "autocomplete",
        "placeholder",
        "name",
        "id"
    ]

    for key in search_keys:

        value = normalize(
            metadata.get(key) or ""
        )

        if not value:
            continue

        for field_name, aliases in FIELD_ALIASES.items():

            for alias in aliases:

                if value == normalize(alias):
                    return field_name

    return None


def fill_fields(detected_fields, profile):

    filled = 0
    skipped = 0

    for item in detected_fields:

        element = item["element"]
        metadata = item["metadata"]

        profile_key = identify_field(metadata)

        field_name = (
            metadata["label"]
            or metadata["name"]
            or metadata["id"]
        )

        if not profile_key:
            print(f"SKIPPED: {field_name}")
            skipped += 1
            continue

        value = profile.get(profile_key)

        if value is None or value == "":
            print(f"MISSING VALUE: {field_name}")
            skipped += 1
            continue

        try:

            if metadata["type"] == "file":

                if profile_key != "resume_path":
                    raise ValueError("Unknown file type")

                file_path = Path(value).resolve()

                if not file_path.is_file():
                    raise FileNotFoundError(file_path)

                element.set_input_files(
                    str(file_path)
                )

            elif metadata["type"] in [
                "text",
                "email",
                "tel",
                "url",
                "number",
                "textarea"
            ] or metadata["tag"] == "textarea":

                live_metadata = element.evaluate("""
                    el => ({
                        id: el.id || "",
                        name: el.name || "",
                        label: Array.from(el.labels || [])
                            .map(label => label.innerText)
                            .join(" ")
                            .trim(),
                        connected: el.isConnected
                    })
                """)

                if not live_metadata["connected"]:

                    print(f"DETACHED: {field_name}")
                    skipped += 1
                    continue

                if profile_key in ["linkedin", "github"]:

                    current_label = (
                        live_metadata["label"].lower()
                    )

                    print("\nSOCIAL PROFILE VERIFICATION")
                    print(f"Profile key: {profile_key}")
                    print(f"Original label: {metadata['label']}")
                    print(f"Current label: {live_metadata['label']}")
                    print(f"Original ID: {metadata['id']}")
                    print(f"Current ID: {live_metadata['id']}")

                    if profile_key not in current_label:

                        print("SKIPPED: Label mismatch")
                        skipped += 1
                        continue

                    if (
                        "linkedin" in current_label
                        and "github" in current_label
                    ):

                        print("SKIPPED: Ambiguous label")
                        skipped += 1
                        continue

                element.fill(
                    str(value),
                    timeout=5000
                )

            elif metadata["type"] in [
                "text",
                "email",
                "tel",
                "url",
                "number",
                "textarea"
            ] or metadata["tag"] == "textarea":

                live_metadata = element.evaluate("""
                    el => ({
                        id: el.id || "",
                        name: el.name || "",
                        label: Array.from(el.labels || [])
                            .map(label => label.innerText)
                            .join(" ")
                            .trim()
                    })
                """)

                print("\nFIELD VERIFICATION")
                print(f"Original label: {metadata['label']}")
                print(f"Original ID: {metadata['id']}")
                print(f"Current label: {live_metadata['label']}")
                print(f"Current ID: {live_metadata['id']}")
                print(f"Profile key: {profile_key}")

                if profile_key in ["linkedin", "github"]:

                    current_label = (
                        live_metadata["label"].lower()
                    )

                    if profile_key not in current_label:

                        print(
                            "SKIPPED: Current label does "
                            "not match the profile key."
                        )

                        skipped += 1
                        continue

                if profile_key in ["linkedin", "github"]:

                    current_label = element.evaluate("""
                        el => Array.from(el.labels || [])
                            .map(label => label.innerText)
                            .join(" ")
                            .trim()
                            .toLowerCase()
                    """)

                    if profile_key not in current_label:

                        print(
                            f"SKIPPED: Label mismatch "
                            f"for {profile_key}"
                        )

                        skipped += 1
                        continue

                    if (
                        "linkedin" in current_label
                        and "github" in current_label
                    ):

                        print("SKIPPED: Ambiguous profile field")

                        skipped += 1
                        continue

                element.fill(str(value))

            else:

                print(f"UNSUPPORTED: {field_name}")
                skipped += 1
                continue

            print(f"FILLED: {field_name}")
            filled += 1

        except Exception as error:

            print(f"ERROR: {field_name} - {error}")
            skipped += 1

    return filled, skipped

import json


def detect_fields(page):

    fields = page.locator(
        "input, select, textarea"
    ).element_handles()

    detected_fields = []

    for field in fields:

        try:

            if not field.is_visible():
                continue

            metadata = field.evaluate("""
                element => ({
                    id: element.id || "",
                    name: element.name || "",
                    tag: element.tagName.toLowerCase(),
                    type: element.type || "",
                    placeholder: element.placeholder || "",
                    autocomplete: element.autocomplete || "",
                    aria_label:
                        element.getAttribute("aria-label") || "",
                    label: Array.from(element.labels || [])
                        .map(label => label.innerText)
                        .join(" ")
                        .trim(),
                    required: element.required,
                    disabled: element.disabled,
                    readonly: element.readOnly
                })
            """)

            if metadata["disabled"] or metadata["readonly"]:
                continue

            if metadata["type"] in [
                "hidden",
                "submit",
                "button",
                "reset"
            ]:
                continue

            stable_locator = None

            # Priority 1: Unique HTML ID

            if metadata["id"]:

                selector = (
                    "[id="
                    + json.dumps(metadata["id"])
                    + "]"
                )

                candidate = page.locator(selector)

                if candidate.count() == 1:
                    stable_locator = candidate

            # Priority 2: Unique HTML name

            if stable_locator is None and metadata["name"]:

                selector = (
                    metadata["tag"]
                    + "[name="
                    + json.dumps(metadata["name"])
                    + "]"
                )

                candidate = page.locator(selector)

                if candidate.count() == 1:
                    stable_locator = candidate

            # Priority 3: Exact associated label

            if stable_locator is None and metadata["label"]:

                candidate = page.get_by_label(
                    metadata["label"],
                    exact=True
                )

                if candidate.count() == 1:
                    stable_locator = candidate

            # Fallback: Original element reference

            if stable_locator is None:
                stable_locator = field

            detected_fields.append({
                "element": stable_locator,
                "metadata": metadata
            })

        except Exception as error:

            print(f"FIELD DETECTION ERROR: {error}")

    return detected_fields

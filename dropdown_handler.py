import re
import time
import json


def is_custom_dropdown(element):

    return element.evaluate("""
        el => {
            const role = el.getAttribute("role");
            const popup = el.getAttribute("aria-haspopup");
            const autocomplete =
                el.getAttribute("aria-autocomplete");

            return (
                role === "combobox" ||
                popup === "listbox" ||
                autocomplete === "list" ||
                autocomplete === "both"
            );
        }
    """)


def get_search_values(profile_key, value, profile):

    values = [str(value)]

    # ==========================================
    # COUNTRY SEARCH VALUES
    # ==========================================

    if profile_key == "country":

        if str(value).strip().lower() == "united states":

            values.extend([
                "United States of America",
                "US",
                "USA",
                "+1"
            ])

    # ==========================================
    # CITY SEARCH VALUES
    # ==========================================

    if profile_key == "city":

        city = profile.get("city", "")
        state = profile.get("state", "")
        country = profile.get("country", "")

        if city and state:
            values.append(f"{city}, {state}")

        if city and state and country:
            values.append(f"{city}, {state}, {country}")

    return list(dict.fromkeys(values))


def option_matches(text, profile_key, value, profile):

    text = " ".join(text.lower().split())
    value = " ".join(str(value).lower().split())

    # ==========================================
    # COUNTRY MATCHING
    # ==========================================

    if profile_key == "country":

        if text == value:
            return True

        if value == "united states":

            accepted_patterns = [
                r"united states",
                r"united states of america",
                r"united states\s*\(\+1\)",
                r"united states\s*\+1",
                r"united states\s*\(us\)",
                r"united states\s*\(usa\)",
                r"\+1\s*united states",
                r"united states\s*\(us\)\s*\+1",
                r"us",
                r"usa"
            ]

            return any(
                re.fullmatch(pattern, text)
                for pattern in accepted_patterns
            )

        return False

    # ==========================================
    # CITY MATCHING
    # ==========================================

    if profile_key == "city":

        city = profile.get("city", "").lower()
        state = profile.get("state", "").lower()

        abbreviation = profile.get(
            "state_abbreviation", ""
        ).lower()

        city_matches = bool(
            city and re.search(
                r"\b" + re.escape(city) + r"\b",
                text
            )
        )

        state_matches = bool(
            state and re.search(
                r"\b" + re.escape(state) + r"\b",
                text
            )
        )

        abbreviation_matches = bool(
            abbreviation and re.search(
                r"\b" + re.escape(abbreviation) + r"\b",
                text
            )
        )

        return (
            city_matches
            and (state_matches or abbreviation_matches)
        )

    # ==========================================
    # EXACT MATCHING
    # ==========================================

    if text == value:
        return True

    # ==========================================
    # STATE MATCHING
    # ==========================================

    if profile_key == "state":

        abbreviation = profile.get(
            "state_abbreviation", ""
        ).lower()

        return bool(
            abbreviation and text == abbreviation
        )

    return False

    if text == value:
        return True

    if profile_key == "state":

        abbreviation = profile.get(
            "state_abbreviation", ""
        ).lower()

        return bool(
            abbreviation and text == abbreviation
        )

    return False


def fill_custom_dropdown(
    element,
    profile_key,
    value,
    profile
):

    print(f"DROPDOWN DETECTED: {profile_key}")

    search_values = get_search_values(
        profile_key,
        value,
        profile
    )

    for search_value in search_values:

        try:

            element.scroll_into_view_if_needed(
                timeout=5000
            )

            element.click(timeout=5000)

            editable = element.evaluate("""
                el => (
                    el.tagName === "INPUT" &&
                    !el.readOnly &&
                    !el.disabled
                )
            """)

            if editable:

                element.fill(
                    search_value,
                    timeout=5000
                )

            deadline = time.monotonic() + 6

            while time.monotonic() < deadline:

                options = element.evaluate("""
                    el => {

                        const ids = [
                            el.getAttribute("aria-controls"),
                            el.getAttribute("aria-owns")
                        ]
                        .filter(Boolean)
                        .join(" ")
                        .split(/\\s+/)
                        .filter(Boolean);

                        const results = [];

                        for (const id of ids) {

                            const container =
                                document.getElementById(id);

                            if (!container) continue;

                            for (const option of
                                container.querySelectorAll(
                                    '[role="option"]'
                                )) {

                                if (
                                    option.id &&
                                    option.getClientRects().length &&
                                    option.getAttribute(
                                        "aria-disabled"
                                    ) !== "true"
                                ) {

                                    results.push({
                                        id: option.id,
                                        text: option.innerText
                                    });

                                }
                            }
                        }

                        return results;
                    }
                """)

                if profile_key == "country" and options:

                    print("\nCOUNTRY OPTIONS DETECTED:")

                    for option in options:

                        print(
                            f"  Option: {option['text']!r}"
                        )

                matching_options = [
                    option for option in options
                    if option_matches(
                        option["text"],
                        profile_key,
                        value,
                        profile
                    )
                ]

                if len(matching_options) == 1:

                    selected = matching_options[0]

                    clicked = element.evaluate("""
                        (el, optionId) => {

                            const option =
                                document.getElementById(
                                    optionId
                                );

                            if (!option) return false;

                            if (
                                option.getAttribute("role")
                                !== "option"
                            ) return false;

                            const ids = [
                                el.getAttribute("aria-controls"),
                                el.getAttribute("aria-owns")
                            ]
                            .filter(Boolean)
                            .join(" ")
                            .split(/\\s+/);

                            const associated = ids.some(id => {

                                const container =
                                    document.getElementById(id);

                                return container &&
                                    container.contains(option);
                            });

                            if (!associated) return false;

                            option.click();

                            return true;
                        }
                    """, selected["id"])

                    if clicked:

                        print(
                            "DROPDOWN OPTION CLICKED: "
                            f"{selected['text']}"
                        )

                        return True

                time.sleep(0.25)

            print(
                f"NO MATCH FOR SEARCH: {search_value}"
            )

            element.press("Escape", timeout=2000)

        except Exception as error:

            print(
                f"DROPDOWN ERROR: "
                f"{profile_key} - {error}"
            )

    print(f"DROPDOWN MATCH NOT FOUND: {profile_key}")

    return False

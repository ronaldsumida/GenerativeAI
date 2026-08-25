---
name: itinerary-publisher
description: Create an attractive editable Word DOCX version of an established travel itinerary, using a compact three-column day-by-day layout with color-coded transportation, activities, and lodging. Use when the user asks to print, publish, export, download, or create a Word/DOCX itinerary.
---

# Itinerary Publisher

Publish the itinerary already established in the conversation. Do not re-read Outlook or re-plan the trip unless essential information is missing.

The visual design intentionally resembles a practical hand-built travel itinerary: a full-width date band for each day, transportation on the left, plans in the middle, and lodging on the right. See `references/document-style-guide.md`.

## Content discipline

The Word document is a concise travel reference, not an archive of every fact found in the correspondence.

- Include operationally useful information: dates, routes, times, flight/train numbers, lodging, addresses, confirmation/record locators, seats, transfers, booked activities, and important meeting/pickup instructions.
- **Do not include prices, fares, room rates, taxes, fees, totals, amounts paid, balances, currency amounts, or other pricing information**, even if those details appeared in the e-mails or earlier conversation.
- Do not add promotional text, loyalty-program marketing, cancellation policies, boilerplate terms, or verbose booking-provider language unless the user specifically asks for it.
- Do not add destination recommendations or decorative prose that were not part of the established itinerary.

## Rendering workflow

1. Convert the established itinerary to the JSON shape below, applying the content discipline above.
2. Run `scripts/render_itinerary.py` with that JSON as its single command-line argument.
3. The script prints JSON containing `filename`.
4. Tell the user the Word document is ready and include a markdown link exactly like:
   `[Download the itinerary](/itineraries/<filename>)`

The app automatically detects that link and shows a preview in the main pane. Do not add a separate preview link.

## JSON shape

```json
{
  "title": "Optional trip title",
  "days": [
    {
      "date": "Monday, Sept. 21",
      "transportation": [
        {
          "title": "Cathay Pacific 603",
          "lines": ["HKG - KTM", "6:55 p.m. - 9:45 p.m."]
        }
      ],
      "plans": [
        {
          "title": "Fly to Kathmandu (A330)",
          "lines": ["R/L #EDA3TW", "Seats 14A and 14C", "Driver will be waiting to take us to the hotel"],
          "kind": "travel"
        }
      ],
      "lodging": {
        "title": "Dalai-La Boutique Hotel",
        "lines": ["Chaksibari Marg, Thamel", "Kathmandu 44600", "Expedia #72076541213989"],
        "full_details": true
      }
    }
  ]
}
```

`plans[].kind` may be `activity` for a booked excursion/ticket (pale yellow) or `travel`/`note` for ordinary unshaded text. Set `lodging.full_details` true on the first day a property's address/confirmation details are shown; later days may carry only the hotel name with false.

Keep the document faithful to known facts and omit pricing information.

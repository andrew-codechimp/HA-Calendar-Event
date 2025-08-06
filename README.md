# HA-Calendar-Event

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![Downloads][download-latest-shield]]()
[![HACS Installs][hacs-installs-shield]]()
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

Calendar Event Helpers for Home Assistant

Allows creation of binary sensor helper that look at the summary of the currently active event for a calendar, turning the sensor on if the summary matches that configured in the helper.
The description of the calendar event is available as an attribute within the helper.


_Please :star: this repo if you find it useful_  
_If you want to show your support please_

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png)](https://www.buymeacoffee.com/codechimp)

![Helper Calendar Event](https://raw.githubusercontent.com/andrew-codechimp/ha-calendar-event/main/images/screenshot.png "Helper Calendar Event")

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrew-codechimp&repository=HA-Calendar-Event&category=Integration)

Restart Home Assistant

In the HA UI go to "Configuration" -> "Devices & services" -> "Helpers" click "+" and select "Calendar Event"

### Manual Installation

<details>
<summary>Show detailed instructions</summary>

Installation via HACS is recommended, but a manual setup is supported.

1. Manually copy custom_components/calendar_event folder from latest release to custom_components folder in your config folder.
1. Restart Home Assistant.
1. In the HA UI go to "Configuration" -> "Devices & services" -> "Helpers" click "+" and select "Calendar Event"

</details>

## Usage

A new Calendar Event helper will be available within Settings/Helpers or click the My link to jump straight there

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=calendar_event)


### Translations

You can help by adding missing translations when you are a native speaker. Or add a complete new language when there is no language file available.

Calendar Event uses Crowdin to make contributing easy.

<details>
<summary>Instructions</summary>

**Changing or adding to existing language**

First register and join the translation project

- If you don’t have a Crowdin account yet, create one at [https://crowdin.com](https://crowdin.com)
- Go to the [Calendar Event Crowdin project page](https://crowdin.com/project/calendar-event)
- Click Join.

Next translate a string

- Select the language you want to contribute to from the dashboard.
- Click Translate All.
- Find the string you want to edit, missing translation are marked red.
- Fill in or modify the translation and click Save.
- Repeat for other translations.

Calendar Event will automatically pull in latest changes to translations every day and create a Pull Request. After that is reviewed by a maintainer it will be included in the next release of Calendar Event.

**Adding a new language**

Create an [Issue](https://github.com/andrew-codechimp/HA-Calendar-Event/issues/) requesting a new language. We will do the necessary work to add the new translation to the integration and Crowdin site, when it's ready for you to contribute we'll comment on the issue you raised.

</details>

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/andrew-codechimp/HA-Calendar-Event.svg?style=for-the-badge
[commits]: https://github.com/andrew-codechimp/HA-Calendar-Event/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge
[exampleimg]: example.png
[license-shield]: https://img.shields.io/github/license/andrew-codechimp/HA-Calendar-Event.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/andrew-codechimp/HA-Calendar-Event.svg?style=for-the-badge
[releases]: https://github.com/andrew-codechimp/HA-Calendar-Event/releases
[download-latest-shield]: https://img.shields.io/github/downloads/andrew-codechimp/HA-Calendar-Event/latest/total?style=for-the-badge
[hacs-installs-shield]: https://img.shields.io/endpoint.svg?url=https%3A%2F%2Flauwbier.nl%2Fhacs%2Fcalendar_event&style=for-the-badge

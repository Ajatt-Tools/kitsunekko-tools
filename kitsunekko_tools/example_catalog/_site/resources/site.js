/**
 *
 * @licstart  The following is the entire license notice for the
 *  JavaScript code in this page.
 *
 * Copyright (C) 2026  Ajatt-Tools and contributors
 *
 * The JavaScript code in this page is free software: you can
 * redistribute it and/or modify it under the terms of the GNU Affero
 * General Public License as published by the Free Software Foundation,
 * either version 3 of the License, or (at your option) any later version.
 *
 * The code is distributed WITHOUT ANY WARRANTY; without even the
 * implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU Affero General Public License for more details.
 *
 * As additional permission under GNU Affero General Public License
 * section 7, you may distribute non-source (e.g., minimized or compacted)
 * forms of that code without the copy of the GNU Affero General Public
 * License normally required by section 4, provided you include this
 * license notice and a URL through which recipients can access the
 * Corresponding Source.
 *
 * @licend  The above is the entire license notice
 * for the JavaScript code in this page.
 *
 */

(function () {
    "use strict";

    function dateTimeZoneShort(date) {
        const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const format = new Intl.DateTimeFormat("en", {
            timeZone: timeZone,
            timeZoneName: "short",
        });
        return format.formatToParts(date).find(part => part.type === "timeZoneName").value;
    }

    function formatUnixTimestamp(timestamp) {
        const date = new Date(timestamp * 1000);

        // Format according to strftime("%d %b %Y %H:%M:%S") pattern
        // <td data-cell="Last modified" class="last_modified"><span class="font-mono">15 Dec 2025 07:13:38</span></td>

        const day = date.getDate().toString().padStart(2, "0");
        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const month = months[date.getMonth()];
        const year = date.getFullYear();

        const hours = date.getHours().toString().padStart(2, "0");
        const minutes = date.getMinutes().toString().padStart(2, "0");
        const seconds = date.getSeconds().toString().padStart(2, "0");

        return `${day} ${month} ${year} ${hours}:${minutes}:${seconds}`;
    }

    function updateHeader() {
        // Update the header to show timezone
        for (const lastModifiedHeader of document.querySelectorAll("th.last_modified")) {
            const tzAbbreviation = dateTimeZoneShort(new Date());
            lastModifiedHeader.textContent = `Last modified (${tzAbbreviation})`;
        }
    }

    function updateRows() {
        // Update the rows to show timezone
        for (const entry of document.querySelectorAll(".entries_table tr")) {
            const timestamp = entry.getAttribute("data-timestamp");
            const last_modified = entry.querySelector("td.last_modified .font-mono");
            if (timestamp && last_modified) {
                last_modified.textContent = formatUnixTimestamp(timestamp);
            }
        }
    }

    function main() {
        updateHeader();
        updateRows();
    }

    document.addEventListener("DOMContentLoaded", main);
})();

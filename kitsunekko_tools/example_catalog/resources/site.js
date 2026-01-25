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

    // Sort direction constants
    const SortDirection = {
        ASC: "sort-asc",
        DESC: "sort-desc"
    };

    // Sort state data class
    class SortState {
        constructor(column = null, isAscending = true) {
            this.currentSortColumn = column;
            this.isAscending = isAscending; // boolean to indicate sort direction
        }

        // Get the string representation of sort direction
        get direction() {
            return this.isAscending ? SortDirection.ASC : SortDirection.DESC;
        }

        // Toggle sort direction for a column
        toggleDirection(column) {
            if (this.currentSortColumn === column) {
                // Second click sorts in reverse
                this.isAscending = !this.isAscending;
            } else {
                this.isAscending = true;
                this.currentSortColumn = column;
            }
            return this.direction;
        }
    }

    // Single instance of sort state for the page
    const sortState = new SortState();

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

    // Get sort value for a row based on column class
    function getSortValue(row, columnClass) {
        switch (columnClass) {
            case "file_size":
                return parseInt(row.getAttribute("data-file-size")) || 0;
            case "entry_type": // Type column
                return row.getAttribute("data-entry-type") || "";
            case "last_modified": // Last modified column
                return parseInt(row.getAttribute("data-timestamp")) || 0;
            default:
                const node = row.querySelector(`.${columnClass}`);
                return node ? node.textContent.toLowerCase() : "";
        }
    }

    // Compare function for sorting
    function compareRows(rowA, rowB, columnClass) {
        const valueA = getSortValue(rowA, columnClass);
        const valueB = getSortValue(rowB, columnClass);

        let comparison = 0;
        if (typeof valueA === "string" && typeof valueB === "string") {
            comparison = valueA.localeCompare(valueB);
        } else if (typeof valueA === "number" && typeof valueB === "number") {
            comparison = valueA - valueB;
        } else {
            comparison = String(valueA).localeCompare(String(valueB));
        }

        return sortState.isAscending ? comparison : -comparison;
    }

    // Sort table rows by column with class "columnClass".
    function sortTable(entries_table, columnClass) {
        const tbody = entries_table.querySelector("tbody");
        const rows = Array.from(
            // Get all sortable rows in tbody.
            tbody.querySelectorAll("tr:not(.subtitle_catalog_end):not([data-entry-type='unsorted'])"),
        );

        sortState.toggleDirection(columnClass);

        rows.sort((rowA, rowB) => {
            return compareRows(rowA, rowB, columnClass);
        });

        // Re-append rows to tbody in sorted order
        rows.forEach(row => tbody.prepend(row));

        updateSortDirectionIndicators(entries_table);
    }

    // Update header indicators to show sort direction (▲/▼).
    function updateSortDirectionIndicators(entries_table) {
        // Clear previous indicators
        entries_table.querySelectorAll("thead th").forEach(header => {
            header.classList.remove(SortDirection.ASC, SortDirection.DESC, "sort-indicator");
        });

        // Add indicator to current sort column
        if (sortState.currentSortColumn) {
            const currentHeader = entries_table.querySelector(`thead th.${sortState.currentSortColumn}`);
            if (currentHeader) {
                currentHeader.classList.add(sortState.direction, "sort-indicator");
            }
        }
    }

    // Add event listeners to table headers for sorting
    function addSortingListeners() {
        const sort_by = ["entry_name", "file_size", "entry_type", "english_name", "japanese_name", "last_modified"];
        document.querySelectorAll(".entries_table").forEach(entries_table => {
            // We have one table on the main page, but up to 3 tables on each entry page.
            entries_table.querySelectorAll("thead th").forEach(header => {
                const columnClass = Array.from(header.classList).find(class_name => sort_by.includes(class_name));
                if (columnClass) {
                    header.addEventListener("click", () => {
                        sortTable(entries_table, columnClass);
                    });
                }
            });
        });
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
        addSortingListeners();
    }

    document.addEventListener("DOMContentLoaded", main);
})();

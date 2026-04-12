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
        DESC: "sort-desc",
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
    function compareRows(valueA, valueB) {
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

    function getSortableRows(tbody) {
        return Array.from(
            // Get all sortable rows in tbody.
            tbody.querySelectorAll("tr:not(.subtitle_catalog_end):not([data-entry-type='unsorted'])"),
        );
    }

    // Sort table rows by column with class "columnClass".
    function sortTable(entries_table, columnClass) {
        const tbody = entries_table.querySelector("tbody");
        sortState.toggleDirection(columnClass);
        entries_table.setAttribute("data-is-sorting", true);

        // Use setTimeout to allow UI to update before starting heavy operation
        setTimeout(() => {
            try {
                // Pre-compute sort values.
                const sortData = getSortableRows(tbody).map(row => ({
                    row: row,
                    sort_value: getSortValue(row, columnClass),
                }));

                // Sort the pre-computed data
                sortData.sort((rowA, rowB) => compareRows(rowA.sort_value, rowB.sort_value));

                // Update the DOM by using DocumentFragment
                const fragment = document.createDocumentFragment();
                sortData.forEach(item => fragment.appendChild(item.row));

                tbody.prepend(fragment);
            } finally {
                entries_table.removeAttribute("data-is-sorting");
                updateSortDirectionIndicators(entries_table);
            }
        }, 0);
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
                    header.setAttribute("title", "Click to sort Table by this column.");
                    header.addEventListener("click", () => {
                        sortTable(entries_table, columnClass);
                    });
                }
            });
        });
    }

    function adjustModTimeColumnNameToLocalTimeZone() {
        // Update the header to show the local timezone abbreviation.
        for (const lastModifiedHeader of document.querySelectorAll("th.last_modified")) {
            const tzAbbreviation = dateTimeZoneShort(new Date());
            lastModifiedHeader.textContent = `Last modified (${tzAbbreviation})`;
        }
    }

    function adjustTableRowsToLocalTimeZone() {
        // Update all data rows to show modification times in local time zone.
        for (const entry of document.querySelectorAll(".entries_table tr")) {
            const timestamp = entry.getAttribute("data-timestamp");
            const last_modified = entry.querySelector("td.last_modified .font-mono");
            if (timestamp && last_modified) {
                last_modified.textContent = formatUnixTimestamp(timestamp);
            }
        }
    }

    // Multi-file download with checkboxes

    /**
     * Get all file checkboxes within a section.
     * @param {HTMLElement} section
     * @returns {HTMLInputElement[]}
     */
    function getFileCheckboxes(section) {
        // <input type="checkbox" class="file-checkbox" ... >
        return Array.from(section.querySelectorAll(".file-checkbox"));
    }

    /**
     * Get the count of checked file checkboxes in a section.
     * @param {HTMLElement} section
     * @returns {number}
     */
    function countSelectedSubtitleFiles(section) {
        return getFileCheckboxes(section).filter(cb => cb.checked).length;
    }

    /**
     * Update the "Select all" / "Deselect all" button text based on checked count.
     * @param {HTMLElement} section
     * @param {number} checkedCount
     */
    function updateSelectAllButtonText(section, checkedCount) {
        const selectAllFilesButton = section.querySelector(".select-all-btn");
        const totalFileCount = getFileCheckboxes(section).length;
        if (selectAllFilesButton) {
            selectAllFilesButton.textContent = checkedCount === totalFileCount ? "Deselect all" : "Select all";
        }
    }

    /**
     * Update the download button's selected count and disabled state.
     * @param {HTMLElement} section
     * @param {number} checkedCount
     */
    function updateSelectedSubtitleCount(section, checkedCount) {
        const downloadButton = section.querySelector(".download-selected-btn");
        const selectedCountSpan = section.querySelector(".selected-count");
        if (downloadButton && selectedCountSpan) {
            selectedCountSpan.textContent = String(checkedCount);
            downloadButton.disabled = checkedCount === 0;
        }
    }

    /**
     * Update the download button's selected count and disabled state for a section.
     * Also updates the "Select all" / "Deselect all" button text.
     * @param {HTMLElement} section
     */
    function updateDownloadBar(section) {
        const checkedCount = countSelectedSubtitleFiles(section);
        updateSelectAllButtonText(section, checkedCount);
        updateSelectedSubtitleCount(section, checkedCount);
    }

    /**
     * Toggle all file checkboxes within the section.
     * If all are checked, uncheck all; otherwise, check all.
     * @param {HTMLElement} section
     */
    function toggleSelectAll(section) {
        const checkboxes = getFileCheckboxes(section);
        const allChecked = checkboxes.every(cb => cb.checked);
        checkboxes.forEach(cb => {
            cb.checked = !allChecked;
        });
        updateDownloadBar(section);
    }

    /**
     * Trigger a browser download from a Blob.
     * @param {Blob} blob
     * @param {string} filename
     */
    function triggerBlobDownload(blob, filename) {
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        try {
            anchor.href = url;
            anchor.download = filename;
            document.body.appendChild(anchor);
            anchor.click();
        } finally {
            anchor.remove();
            URL.revokeObjectURL(url);
        }
    }

    /**
     * Fetch a single file as a blob, returning its filename and data.
     * @param {string} url
     * @param {string} filename
     * @returns {Promise<{filename: string, blob: Blob}>}
     */
    async function fetchFileAsBlob(url, filename) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`Failed to fetch ${filename}: ${response.status} ${response.statusText}`);
        }
        return { filename: filename, blob: await response.blob() };
    }

    /**
     * Fetch the file associated with a checkbox element as a blob.
     * @param {HTMLInputElement} checkbox
     * @returns {Promise<{filename: string, blob: Blob}>}
     */
    function fetchCheckboxFile(checkbox) {
        return fetchFileAsBlob(checkbox.getAttribute("data-download-url"), checkbox.getAttribute("data-filename"));
    }

    /**
     * Fetch a file by URL and trigger its download.
     * @param {string} url
     * @param {string} filename
     */
    function fetchAndDownload(url, filename) {
        fetchFileAsBlob(url, filename)
            .then(({ blob, filename }) => triggerBlobDownload(blob, filename))
            .catch(error => alert(`Download failed: ${error.message}`));
    }

    /**
     * Fetch and download the file associated with a single checkbox.
     * @param {HTMLInputElement} checkbox
     */
    function downloadSingleFile(checkbox) {
        fetchAndDownload(
            checkbox.getAttribute("data-download-url"),
            checkbox.getAttribute("data-filename"),
        );
    }

    /**
     * Create a zip archive from fetched file results and trigger its download.
     * @param {{filename: string, blob: Blob}[]} results
     * @param {string} entryName
     * @returns {Promise<void>}
     */
    function zipAndDownload(results, entryName) {
        const zip = new JSZip();
        results.forEach(({ filename, blob }) => zip.file(filename, blob));
        return zip.generateAsync({ type: "blob" }).then(zipBlob => triggerBlobDownload(zipBlob, `${entryName}.zip`));
    }

    /**
     * Download selected files as a zip archive using JSZip.
     * If only one file is selected, download it directly.
     * @param {HTMLElement} section
     */
    function downloadSelected(section) {
        const checked = getFileCheckboxes(section).filter(checkbox => checkbox.checked);
        if (checked.length === 0) {
            return;
        }

        if (checked.length === 1) {
            downloadSingleFile(checked[0]);
            return;
        }

        // Multiple files: fetch all, then zip.
        const entryName = section.getAttribute("data-entry-name") || "subtitles";
        section.setAttribute("data-is-downloading", "true");
        Promise.all(checked.map(fetchCheckboxFile))
            .then(results => zipAndDownload(results, entryName))
            .catch(error => alert(`Download failed: ${error.message}`))
            .finally(() => section.removeAttribute("data-is-downloading"));
    }

    /**
     * Initialize checkbox listeners and download buttons for all entry sections.
     */
    function initDownloadCheckboxes() {
        for (const section of document.querySelectorAll("section[data-entry-name]")) {
            // "Select all" button.
            const selectAllBtn = section.querySelector(".select-all-btn");
            if (selectAllBtn) {
                selectAllBtn.addEventListener("click", () => toggleSelectAll(section));
            }

            // Individual file checkboxes.
            for (const checkbox of getFileCheckboxes(section)) {
                checkbox.addEventListener("change", () => updateDownloadBar(section));
            }

            // "Download selected" button.
            const downloadBtn = section.querySelector(".download-selected-btn");
            if (downloadBtn) {
                downloadBtn.addEventListener("click", () => downloadSelected(section));
            }

            // Intercept direct link clicks to force download (cross-origin URLs ignore the download attribute).
            for (const link of section.querySelectorAll("a[download]")) {
                link.addEventListener("click", event => {
                    event.preventDefault();
                    fetchAndDownload(link.href, link.download);
                });
            }
        }
    }

    function main() {
        adjustModTimeColumnNameToLocalTimeZone();
        adjustTableRowsToLocalTimeZone();
        addSortingListeners();
        initDownloadCheckboxes();
    }

    document.addEventListener("DOMContentLoaded", main);
})();

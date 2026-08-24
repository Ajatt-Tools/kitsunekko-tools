// Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { JSDOM } from "jsdom";

const dirname = path.dirname(fileURLToPath(import.meta.url));
const siteScriptPath = path.join(dirname, "..", "resources", "site.js");
const siteScript = fs.readFileSync(siteScriptPath, "utf8");

type SectionOptions = {
    type: string;
    count: number;
};

type BootSiteOptions = {
    sections?: SectionOptions[];
};

/**
 * Build one subtitle checkbox table row for the test DOM.
 * @param sectionType Subtitle format represented by the row.
 * @param index One-based row index.
 * @returns HTML for one checkbox row.
 */
function checkboxRow(sectionType: string, index: number): string {
    return `
    <tr data-timestamp="${index}" data-file-size="${index}">
      <td data-cell="#" class="entry_number"><span class="font-mono">${index}</span></td>
      <td data-cell="Name" class="entry_name">
        <input type="checkbox" class="file-checkbox" data-download-url="/subtitles/${sectionType}/${index}.srt" data-filename="${sectionType}-${index}.srt">
        <a href="/subtitles/${sectionType}/${index}.srt" download="${sectionType}-${index}.srt">${sectionType}-${index}.srt</a>
      </td>
      <td data-cell="Size" class="file_size"><span class="font-mono">${index} B</span></td>
      <td data-cell="Last modified" class="last_modified"><span class="font-mono">01 Jan 2026 00:00:00</span></td>
    </tr>`;
}

/**
 * Build one subtitle format section for the test DOM.
 * @param options Subtitle format and number of rows to create.
 * @returns HTML for one subtitle section.
 */
function subtitleSection({ type, count }: SectionOptions): string {
    return `
    <section class="group_${type}" data-entry-name="Example ${type}">
      <div class="button_row_container download_bar">
        <button type="button" class="select-all-btn">Select all</button>
        <button type="button" class="download-selected-btn" disabled>Download selected (<span class="selected-count">0</span>)</button>
      </div>
      <table class="entries_table file_list_table">
        <thead>
          <tr>
            <th scope="col" class="entry_number">#</th>
            <th scope="col" class="entry_name">Name</th>
            <th scope="col" class="file_size">Size</th>
            <th scope="col" class="last_modified">Last modified (UTC)</th>
          </tr>
        </thead>
        <tbody>${Array.from({ length: count }, (_, index) => checkboxRow(type, index + 1)).join("")}</tbody>
      </table>
    </section>`;
}

/**
 * Create an isolated catalog DOM containing the requested subtitle sections.
 * @param options Optional section definitions.
 * @returns The isolated JSDOM instance.
 */
function makeSiteDom({ sections = [{ type: "srt", count: 4 }] }: BootSiteOptions = {}): JSDOM {
    return new JSDOM(`<main class="no-js">${sections.map(subtitleSection).join("")}</main>`, {
        runScripts: "outside-only",
        url: "https://subtitles.example.test/anime_tv/example.html",
    });
}

/**
 * Evaluate the production site script and trigger its initialization event.
 * @param win Window belonging to the isolated test DOM.
 */
function loadSiteScript(win: Window): void {
    win.eval(`${siteScript}\n//# sourceURL=file://${siteScriptPath}`);
    win.document.dispatchEvent(new win.Event("DOMContentLoaded"));
}

/**
 * Create and initialize an isolated catalog page for a test.
 * @param options Optional section definitions.
 * @returns The DOM, its window, and initialized subtitle sections.
 */
export function bootSite(options: BootSiteOptions = {}): { dom: JSDOM; win: Window; sections: HTMLElement[] } {
    const dom = makeSiteDom(options);
    const win = dom.window;
    win.URL.createObjectURL = () => "blob:subtitles-test";
    win.URL.revokeObjectURL = () => {};
    loadSiteScript(win);
    return {
        dom,
        win,
        sections: [...win.document.querySelectorAll("section[data-entry-name]")] as HTMLElement[],
    };
}

/**
 * Return all file checkboxes in a subtitle section.
 * @param section Subtitle section to query.
 * @returns File checkboxes in document order.
 */
export function checkboxes(section: HTMLElement): HTMLInputElement[] {
    return [...section.querySelectorAll(".file-checkbox")] as HTMLInputElement[];
}

/**
 * Dispatch a realistic checkbox click with an optional Shift modifier.
 * @param win Window used to construct the mouse event.
 * @param checkbox Checkbox receiving the click.
 * @param shiftKey Whether the Shift key is pressed.
 */
export function clickCheckbox(win: Window, checkbox: HTMLInputElement, shiftKey = false): void {
    checkbox.dispatchEvent(new win.MouseEvent("click", { bubbles: true, shiftKey }));
}

/**
 * Read the displayed selected-file count from a subtitle section.
 * @param section Subtitle section to query.
 * @returns Displayed selected-file count.
 */
export function selectedCount(section: HTMLElement): string {
    return section.querySelector(".selected-count")?.textContent ?? "";
}

/**
 * Return the download button from a subtitle section.
 * @param section Subtitle section to query.
 * @returns The section's download button.
 */
export function downloadButton(section: HTMLElement): HTMLButtonElement {
    const win = section.ownerDocument.defaultView;
    const button = section.querySelector(".download-selected-btn");
    if (!win || !(button instanceof win.HTMLButtonElement)) {
        throw new Error("download button not found");
    }
    return button;
}

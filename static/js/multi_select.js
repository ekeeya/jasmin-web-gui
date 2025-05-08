/*
 * Copyright (c) 2025
 * File created on 2025/5/8
 * By: Emmanuel Keeya
 * Email: ekeeya@thothcode.tech
 *
 * This project is licensed under the GNU General Public License v3.0. You may
 * redistribute it and/or modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This project is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
 * without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along with this project.
 * If not, see <http://www.gnu.org/licenses/>.
 *
 */

function initializeMultiSelect(availableSelector, selectedSelector) {
    // Move selected items from available to selected
    $(availableSelector).parent().find('.move-right').click(function() {
        $(availableSelector + ' option:selected').each(function() {
            $(this).appendTo(selectedSelector);
        });
        // Ensure all options in selected are marked as selected
        $(selectedSelector + ' option').prop('selected', true);
    });

    // Move selected items from selected to available
    $(selectedSelector).parent().find('.move-left').click(function() {
        $(selectedSelector + ' option:selected').each(function() {
            $(this).appendTo(availableSelector);
        });
        // Update selected options
        $(selectedSelector + ' option').prop('selected', true);
    });

    // Ensure all options in selected are marked as selected before form submission
    $('form').submit(function() {
        $(selectedSelector + ' option').prop('selected', true);
        $(availableSelector + ' option').prop('selected', false);
    });
}

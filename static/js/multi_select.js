/*
 * Copyright (c) 2025
 * File created on 2025/5/8
 * By: Emmanuel Keeya
 * Email: ekeeya@thothcode.tech
 *
 * Initializes dual-list multiselects: available (left) → selected (right).
 */

(function (window, $) {
    "use strict";

    function scheduleRefresh() {
        window.setTimeout(function () {
            refreshJoyceMultiSelects(document);
        }, 50);
    }

    function initJoyceMultiSelects(root) {
        if (!$ || typeof $.fn.multiSelect !== "function") {
            return;
        }

        $(root || document).find("select.joyce-multi-select, select[data-joyce-multiselect]").each(function () {
            var $el = $(this);
            if ($el.data("multiselect")) {
                return;
            }

            $el.multiSelect({
                keepOrder: true,
                cssClass: "joyce-ms",
                selectableHeader: '<div class="ms-header">Available</div>',
                selectionHeader: '<div class="ms-header">Selected</div>',
            });
        });
    }

    function refreshJoyceMultiSelects(root) {
        if (!$ || typeof $.fn.multiSelect !== "function") {
            return;
        }

        $(root || document).find("select.joyce-multi-select, select[data-joyce-multiselect]").each(function () {
            var $el = $(this);
            if ($el.data("multiselect")) {
                $el.multiSelect("refresh");
            } else {
                initJoyceMultiSelects($el.parent());
            }
        });
    }

    window.initJoyceMultiSelects = initJoyceMultiSelects;
    window.refreshJoyceMultiSelects = refreshJoyceMultiSelects;

    $(document).ready(function () {
        initJoyceMultiSelects(document);

        // Create modal open
        $(document).on("click", "[data-modal-open]", scheduleRefresh);

        // Update modal triggers: data-update-trigger-<id>
        $(document).on("click", function (e) {
            var node = e.target;
            while (node && node !== document) {
                if (node.attributes) {
                    for (var i = 0; i < node.attributes.length; i++) {
                        if (node.attributes[i].name.indexOf("data-update-trigger") === 0) {
                            scheduleRefresh();
                            return;
                        }
                    }
                }
                node = node.parentNode;
            }
        });
    });
})(window, window.jQuery);

// Legacy helper used by older dual-<select> markup (move buttons)
function initializeMultiSelect(availableSelector, selectedSelector) {
    $(availableSelector).parent().find(".move-right").click(function () {
        $(availableSelector + " option:selected").each(function () {
            $(this).appendTo(selectedSelector);
        });
        $(selectedSelector + " option").prop("selected", true);
    });

    $(selectedSelector).parent().find(".move-left").click(function () {
        $(selectedSelector + " option:selected").each(function () {
            $(this).appendTo(availableSelector);
        });
        $(selectedSelector + " option").prop("selected", true);
    });

    $("form").submit(function () {
        $(selectedSelector + " option").prop("selected", true);
        $(availableSelector + " option").prop("selected", false);
    });
}

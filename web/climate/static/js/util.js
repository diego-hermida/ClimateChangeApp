/**
 * Increases the app's "Like" counter by 1. The operation is done using AJAX.
 * If the operation has been successful, disables the "Like" button.
 * On the server side, the counter is increased atomically.
 */
function increaseLikeCount() {
    var counter = $("#likeCounter");
    var url = "/like-count";
    $.ajax({
        type: "POST",
        url: url,
        data: null,
        beforeSend: function (xhr, settings) {
            xhr.setRequestHeader("X-CSRFToken", jQuery("[name=csrfmiddlewaretoken]").val());
        },
        success: function (data) {
            if (data.success) {
                counter.html(parseInt(counter.html()) + 1);
                $('#likeButton').addClass('disabled').prop('onclick', null).off('click');
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            console.log('An error occurred while increasing "Like" counter.')
        }
    });
}

/**
 * Resizes the page footer according to the current viewport.
 * When a 'resize' event has been triggered, this operation waits resizeDelay milliseconds to resize the footer again.
 */
function resizeFooter() {
    var resizeDelay = 200;
    var doResize = true;
    var resizer = function () {
        if (doResize) {
            $('#mainComponent').css("padding-bottom", $('#footerComponent').outerHeight() + 20);
            doResize = false;
        }
    };
    setInterval(resizer, resizeDelay);
    resizer();
    $(window).resize(function () {
        doResize = true;
    });
}

/**
 * Moves the screen to the position of an elements. An animation is played while moving.
 * @param elementId
 *      Element identifier. Defaults to '' (top of page).
 * @param leftOffset
 *      Defaults to 0.
 * @param topOffset
 *      Defaults to 0.
 */
function showElement(elementId='', leftOffset=0, topOffset=0) {
    var element = $('#' + elementId);
    element.removeClass('d-none');
    var offset = element.offset();
    offset.left = leftOffset;
    offset.top -= topOffset;
    $('html, body').animate({
        scrollTop: offset.top,
        scrollLeft: offset.left
    });
}

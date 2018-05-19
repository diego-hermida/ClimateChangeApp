function displayHistoricalWeatherHeatmap(startDate, endDate, data, chartId, locale, legendTitleFormat, subDomainTitleFormat) {

    xs = 575.98;
    sm = 767.98;
    md = 991.98;
    lg = 1199.98;

    subdomain_xs = 'x_day';
    subdomain_sm = 'x_day';
    subdomain_md = 'day';
    subdomain_lg = 'x_day';
    subdomain_xl = 'x_day';

    rowlimit_xs = 29;
    rowlimit_sm = 39;
    rowlimit_md = null;
    rowlimit_lg = 74;
    rowlimit_xl = 89;

    function mapSubdomainToWindowSize(size) {
        if (size <= xs)
            return subdomain_xs;
        if (size <= sm)
            return subdomain_sm;
        if (size <= md)
            return subdomain_md;
        if (size <= lg)
            return subdomain_lg;
        return subdomain_xl;
    }

    function mapRowLimitToWindowSize(size) {
        if (size <= xs)
        // 2nd grade equation given the points: (320, 21), (375, 25), (414, 29) -> fitting rows for iPhone 4/5/5S,
        // 6/7/8 and 6p/7p/8p screen widths.
            return Math.round(0.0003174 * size * size + -0.1479 * size + 35.82);
        if (size <= sm)
            return rowlimit_sm;
        if (size <= md)
            return rowlimit_md;
        if (size <= lg)
            return rowlimit_lg;
        return rowlimit_xl;
    }
    var cal = null;
    function drawCalendar() {
        var windowSize = $(window).width();
        var start = new Date(startDate);
        var end = new Date(endDate);
        var chartDiv = $('#' + chartId);

        if (chartDiv.html() !== '') {
            chartDiv.html('');
        }

        cal = new CalHeatMap();
        cal.init({
            itemSelector: '#' + chartId,
            domain: 'year',
            subDomain: mapSubdomainToWindowSize(windowSize),
            subDomainTitleFormat: subDomainTitleFormat,
            legendTitleFormat: legendTitleFormat,
            subDomainDateFormat: function (date) {
                return date.toLocaleDateString(locale);
            },
            itemName: ['°C', '°C'],
            tooltip: true,
            rowLimit: mapRowLimitToWindowSize(windowSize),
            range: end.getFullYear() - start.getFullYear() + 1,
            start: start,
            data: data,
            verticalOrientation: true,
            considerMissingDataAsZero: false,
            legendHorizontalPosition: 'right',
            legendVerticalPosition: 'top',
            legendMargin: [0, 0, 20, 0],
            legend: [-40, -35, -30, -25, -20, -15, -10, -5, 0, 5, 10, 15, 20, 25, 30, 35, 40],
            legendColors: {
                base: "#d3d3d3",
                min: "#40ffd8",
                max: "#f20013"
            }
        });
    }
    drawCalendar();

    $(window).resize(function () {
        if (this.resizeTO) clearTimeout(this.resizeTO);
        this.resizeTO = setTimeout(function () {
            $(this).trigger('resizeEnd');
        }, 500);
    });

    $(window).bind('resizeEnd', function () {
        drawCalendar();
    });

    return cal;
}

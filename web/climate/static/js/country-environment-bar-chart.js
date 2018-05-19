function displayNumber(n, units, locale) {

    /**
     * This function allows formatting numbers with the localized decimal separator.
     * @param locale  A {string}, representing the ISO2 code for a country (e.g. GB, ES, JP, CN...)
     * @returns {string}  The decimal separator (in most cases, ',' or '.')
     */
    function getDecimalSeparator(locale) {
        return 1.1.toLocaleString(locale).substring(1, 2);
    }

    try {
        return n.toFixed(2).replace(/\.?0*$/, '').replace('.', getDecimalSeparator(locale)) + ' ' + units;
    } catch (err) {
        return '-'
    }
}

function displayCountryEnvironmentBarChart(seriesName, data, color, locale, chartId) {

    var series = [{values: data, key: seriesName}];

    nv.addGraph(function () {
        var chart = nv.models.multiBarChart().stacked(false).showControls(false);

        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + y + '</strong>: ' + e + '</div>'
        });
        chart.x(function (d) {
            return d[0]
        });
        chart.y(function (d) {
            return d[1];
        });
        chart.yAxis.tickFormat(function (d) {
            return displayNumber(d, '%', locale)
        });

        chart.yAxis.tickPadding(10);
        chart.yAxis.showMaxMin(false);
        chart.xAxis.showMaxMin(true);
        chart.xAxis.tickPadding(20);
        chart.margin({bottom: 30});
        chart.legend.margin({top: 10, bottom: 20});

        chart.color([color]);
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}


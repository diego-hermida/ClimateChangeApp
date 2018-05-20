function displayLineChartZoom(seriesName, data, units, colors, locale, chartId) {

    var series = [];
    for (var i = 1; i < seriesName.length; i++) {
        series.push({values: [], key: seriesName[i]})
    }
    for (var j = 0; j < data.length; j++) {
        for (var k = 0; k < series.length; k++) {
            series[k]['values'].push({x: +data[j][0], y: +data[j][k + 1]})
        }
    }

    nv.addGraph(function () {
        var chart = nv.models.lineWithFocusChart();
        chart.xTickFormat(function (d) {
            var _d = new Date(d);
            return _d.toLocaleDateString(locale) + ' ' + _d.toLocaleTimeString(locale)
        });
        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + y +
                '</strong><br/><strong>' + key + '</strong>: ' + displayNumberLocalized(e, units, 1, locale) + '</div>'
        });
        chart.height2 = 20;
        chart.showXAxis = false;
        chart.yAxis.tickFormat(function (d) {
            return displayNumberLocalized(d, '', 1, locale);
        });
        chart.yAxis.showMaxMin(false);
        chart.y2Axis.showMaxMin(false);
        chart.yAxis.tickPadding(10);
        chart.y2Axis.tickPadding(10);
        chart.margin({bottom: 30, right: 0, left: 30});
        chart.legend.margin({top: 10, bottom: 20});
        chart.color(colors);
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}


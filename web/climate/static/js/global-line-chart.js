function displayLineChart(data, seriesName, locale, units, colors, chartId) {

    var series = [{values: data, key: seriesName}];

    nv.addGraph(function () {
        var chart = nv.models.lineChart();
        chart.stacked = false;
        chart.showControls = false;
        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + y +
                '</strong>: ' + displayNumberLocalized(e, units, 1, locale) + '</div>';
        });
        chart.x(function (d) {
            return d[0]
        });
        chart.y(function (d) {
            return d[1]
        });
        chart.xAxis.tickFormat(function (d) {
            _d = new Date(d);
            return _d.getFullYear()
        });
        chart.yAxis.tickFormat(function (d) {
            return displayNumberLocalized(d, '', 1, locale);
        });
        chart.showXAxis = true;
        chart.yAxis.showMaxMin(false);
        chart.yAxis.tickPadding(10);
        chart.xAxis.tickPadding(20);
        chart.margin({bottom: 30, left: 52, right: 30});
        chart.legend.margin({bottom: 20});

        chart.color(colors);
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}


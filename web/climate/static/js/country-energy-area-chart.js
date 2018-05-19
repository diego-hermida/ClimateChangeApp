function displayCountryEnergyAreaChart(seriesName, data, locale, chartId) {

    var series = [{'values': data, 'key': seriesName}];

    nv.addGraph(function () {
        var chart = nv.models.stackedAreaChart();
        chart.showControls(false);
        chart.yAxis.showMaxMin(false);
        chart.yAxis.tickFormat(function (d) {
            return displayNumberLocalizedAndWithSuffix(d, 1000, 't', 1, locale)
        });
        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + y + '</strong>: ' + e + '</div>'
        });
        chart.x(function (d) {
            return d[0]
        });
        chart.y(function (d) {
            return d[1]
        });
        chart.showXAxis = true;
        chart.yAxis.tickPadding(10);
        chart.xAxis.tickPadding(20);
        chart.margin({left: 50, right: 30});
        chart.legend.margin({bottom: 20});

        chart.color(["#DC3912"]);
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}


function displayLineChart(seriesName, data, locale, chartId) {

    var series = [];
    for (i = 0; i < seriesName.length; i++) {
        series.push({key: seriesName[i], values: data[i]})
    }

    nv.addGraph(function () {
        var chart = nv.models.lineChart();
        chart.stacked = false;
        chart.showControls = false;
        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + key +
                '</strong><strong>, ' + y + '</strong>: ' + displayNumberLocalized(e, '%', 2, locale) + '</div>'
        });
        chart.x(function (d) {
            return d[0]
        });
        chart.y(function (d) {
            return d[1]
        });
        chart.yAxis.showMaxMin(false);
        chart.yAxis.tickFormat(function (d) {
            return displayNumberLocalized(d, '%', 2, locale)
        });
        chart.showXAxis = true;
        chart.yAxis.tickPadding(10);
        chart.xAxis.tickPadding(20);
        chart.margin({bottom: 30, left: 50, right: 30});
        chart.legend.margin({bottom: 20});

        chart.color(["#DC3912", "#3366CC", "#AAAA11", "#FF9900", "#000000", "#109618"]);
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}
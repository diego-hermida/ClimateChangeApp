function displayRpcLineChart(data, units, locale, chartId) {

    var series = [];
    for (i = 0; i < data.length; i++) {
        series.push({values: data[i].values, key: data[i].key})
    }

    nv.addGraph(function () {
        var chart = nv.models.lineChart();
        chart.x(function (d) {
            return d[0]
        });
        chart.y(function (d) {
            return d[1]
        });
        chart.yAxis.tickFormat(function (d) {
            return displayNumberLocalized(d, '', 1, locale);
        });
        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal text-center"><strong>' + y +
                '</strong><br/><strong>' + key + '</strong>: ' + displayNumberLocalized(e, units, 1, locale) + '</div>'
        });
        chart.height2 = 20;
        chart.showXAxis = false;
        chart.yAxis.showMaxMin(false);
        chart.yAxis.tickPadding(10);
        chart.xAxis.tickPadding(20);
        chart.margin({bottom: 30 });
        chart.legend.margin({top: 10, bottom: 20});
        chart.color(["#3366CC", "#109618", "#FF9900", "#DC3912"]);
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}


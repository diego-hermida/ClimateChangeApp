function displayHistoricalWeatherLineChart(columns, data, units, locale, chartId) {

    var series = [];
    for (var i = 0; i < columns.length; i++) {
        series.push({values: [], key: columns[i]})
    }
    for (var j = 0; j < data.length; j++) {
        for (var k = 0; k < series.length; k++) {
            series[k]['values'].push([data[j][0], data[j][k + 1]])
        }
    }

    nv.addGraph(function () {
        var chart = nv.models.lineChart();
        chart.stacked = false;
        chart.showControls = false;
        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + y +
                '</strong>: ' + displayNumberLocalized(e, units, 1, locale) + '</div>'
        });
        chart.x(function (d) {
            return d[0]
        });
        chart.y(function (d) {
            return d[1]
        });
        chart.showXAxis = true;
        chart.yAxis.tickFormat(function (d) {
            return displayNumberLocalized(d, '', 1, locale);
        });
        chart.yAxis.showMaxMin(false);
        chart.yAxis.tickPadding(10);
        chart.xAxis.tickPadding(20);
        chart.margin({bottom: 30, left: 30, right: 20});
        chart.legend.margin({bottom: 20, left: 5});

        chart.color(["#DC3912", "#0099C6", "#FF9900", "#3366CC", "#109618"]);
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}


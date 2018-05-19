function displayHistoricalWeatherBarChart(columns, data, chartId, units) {

    var series = [];
    for (i = 0; i < columns.length; i++) {
        series.push({values: [], key: columns[i]})
    }
    for (i = 0; i < data.length; i++) {
        for (j = 0; j < series.length; j++) {
            series[j]['values'].push([data[i][0], data[i][j + 6]])
        }
    }

    nv.addGraph(function () {
        var chart = nv.models.multiBarChart().stacked(false).showControls(false);
        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + key + ' (' + y + ') </strong>: ' +
                d3.format('d')(e) + ' ' + units[(Math.round(e) === 1) ? 0 : 1] + '</div>'
        });
        chart.x(function (d) {
            return d[0]
        });
        chart.y(function (d) {
            return d[1];
        });
        chart.yAxis.tickFormat(function (d) {
            return d3.format('d')(d)
        });
        chart.showXAxis = true;
        chart.xAxis.showMaxMin(true);
        chart.yAxis.tickPadding(10);
        chart.xAxis.tickPadding(20);
        chart.margin({bottom: 30, left: 30, right: 15});
        chart.legend.margin({top: 10, bottom: 20});

        chart.color(["#109618", "#990099", "#FF9900", "#3B3EAC", "#DC3912", "#3366CC"]);
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}


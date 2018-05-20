function displayPieChartWithFormattedData(series, units, colors, locale, chartId) {
    __displayChart(series, units, colors, locale, chartId);
}

function displayPieChart(seriesName, data, units, colors, locale, chartId) {
    var series = [];
    for (var i = 0; i < seriesName.length; i++) {
        series.push({l: seriesName[i], v: data[i]})
    }
    __displayChart(series, units, colors, locale, chartId);
}

function __displayChart(series, units, colors, locale, chartId) {
    nv.addGraph(function () {
        var chart = nv.models.pieChart()
            .x(function (d) {
                return d.l
            })
            .y(function (d) {
                return d.v
            })
            .showLabels(false)
            .donut(true)
            .donutRatio(0.35)
        ;
        chart.color(colors);
        chart.margin({left: 0, right: 0, bottom: 0});
        chart.tooltipContent(function (key, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + key + '</strong>: ' +
                displayNumberLocalized(y, units, 2, locale) + '</div>'
        });
        d3.select('#' + chartId + ' svg')
            .datum(series)
            .transition().duration(350)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}

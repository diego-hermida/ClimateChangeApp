function displayAirPollutionPieChart(data, colorschartId) {
    nv.addGraph(function () {
        var chart = nv.models.pieChart()
            .x(function (d) {
                return d.l
            })
            .y(function (d) {
                return d.v
            })
            .showLabels(true)
            .labelThreshold(.05)
            .labelType("percent")
            .donut(true)
            .donutRatio(0.25)
        ;
        chart.color(["#3366CC", "#DC3912", "#FF9900", "#109618", "#990099", "#3B3EAC", "#0099C6", "#DD4477",
            "#66AA00", "#B82E2E", "#316395", "#994499", "#22AA99", "#AAAA11", "#6633CC", "#E67300", "#8B0707",
            "#329262", "#5574A6", "#3B3EAC"]);
        chart.pie.valueFormat(d3.format(',.0d'));
        chart.margin({left: 0, right: 0, bottom: 0});
        chart.tooltipContent(function (key, x, y, e, graph) {
            return '<div class="m-1 font-weight-normal"><strong>' + key + '</strong>: ' + x + '</div>'
        });
        d3.select('#' + chartId + ' svg')
            .datum(data)
            .transition().duration(350)
            .call(chart);
        nv.utils.windowResize(chart.update);
        return chart;
    });
}


function displayAirPollutionStatsTable(columns, stats, locale, tableId) {

    var tableHtml = '';
    for (var i = 1; i < columns.length; i++) {
        tableHtml += "<tr>" +
            "<th scope=\"row\">" + columns[i] + "</th>" +
            '<td><h5 class="mb-1"><span class="badge" style="color: ' + stats[k][1].t +
                '; background-color: ' + stats[k][1].bg + '">' + displayNumberLocalized(stats[k][1].v, '', 1, locale) +
                '</span></h5></td>' +
            '<td><h5 class="mb-1"><span class="badge" style="color: ' + stats[k][2].t +
                '; background-color: ' + stats[k][2].bg + '">' + displayNumberLocalized(stats[k][2].v, '', 1, locale) +
                '</span></h5></td>' +
            '<td><h5 class="mb-1"><span class="badge" style="color: ' + stats[k][0].t +
                '; background-color: ' + stats[k][0].bg + '">' + displayNumberLocalized(stats[k][0].v, '', 1, locale) +
                '</span></h5></td>' +
            "</tr>"
    }
    $('#' + tableId).html(tableHtml)
}


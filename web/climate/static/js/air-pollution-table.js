function displayAirPollutionStatsTable(columns, stats, locale, tableId) {

    var tableHtml = '';
    for (var i = 1; i < columns.length; i++) {
        j = i - 1;
        tableHtml += "<tr>" +
            "<th scope=\"row\">" + columns[i] + "</th>" +
            '<td><h5 class="mb-1"><span class="badge" style="color: ' + stats[j][1].t +
                '; background-color: ' + stats[j][1].bg + '">' + displayNumberLocalized(stats[j][1].v, '', 1, locale) +
                '</span></h5></td>' +
            '<td><h5 class="mb-1"><span class="badge" style="color: ' + stats[j][2].t +
                '; background-color: ' + stats[j][2].bg + '">' + displayNumberLocalized(stats[j][2].v, '', 1, locale) +
                '</span></h5></td>' +
            '<td><h5 class="mb-1"><span class="badge" style="color: ' + stats[j][0].t +
                '; background-color: ' + stats[j][0].bg + '">' + displayNumberLocalized(stats[j][0].v, '', 1, locale) +
                '</span></h5></td>' +
            "</tr>"
    }
    $('#' + tableId).html(tableHtml)
}


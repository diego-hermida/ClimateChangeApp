/**
 * Obtains the decimal separator character for a specific locale.
 * @param locale
 *      A {string}, representing the ISO2 code for a country (e.g. en, es, fr...)
 * @returns {string}
 *      The decimal separator (in most cases, ',' or '.')
 */
function getDecimalSeparator(locale) {
    return 1.1.toLocaleString(locale).substring(1, 2);
}

/**
 * Formats a number so as to be displayed.
 * @param n
 *      The number to be displayed.
 * @param units
 *      Prints the number followed by a blankspace and this value. Defaults to ''. Example: "2.35 km"
 * @param maxDecimalPlaces
 *      Maximum decimal places. Number will be rounded. Defaults to 2.
 * @param locale
 *      Formats the number according to the specified locale. Defaults to 'en'. Example: 2.3884 -- (es) --> 2,39
 * @param errorRepresentation
 *      If any error occurs during the formatting process, it will return this instead. Defaults to '?'.
 * @returns {string}
 */
function displayNumberLocalized(n, units='', maxDecimalPlaces=2, locale='en', errorRepresentation='?') {

    try {
        if (typeof n === 'string')
            n = parseFloat(n.replace(getDecimalSeparator(locale), '.'));
        return n.toFixed(maxDecimalPlaces).replace(/\.0*$/, '').replace(
            '.', getDecimalSeparator(locale)) + ' ' + units;
    } catch (err) {
        return errorRepresentation
    }
}

/**
 * Formats a number so as to be displayed, but also formats the number according to the Metric System.
 * @param n
 *      The number to be displayed.
 * @param multiplierFactor
 *      This parameter allows the number to be correctly displayed if the number units are different from the base unit.
 *      Defaults to 1. Example: If we have 1943.442 kt, we must use multiplierFactor=1000 (since k = 1000). This will
 *      display the number as follows: '1.94 Mt'
 * @param units
 *      Prints the number followed by a blankspace and this value. Defaults to ''. Example: "2.35 km"
 * @param maxDecimalPlaces
 *      Maximum decimal places. Number will be rounded. Defaults to 2.
 * @param locale
 *      Formats the number according to the specified locale. Defaults to 'en'. Example: 2.3884 -- (es) --> 2,39
 * @param errorRepresentation
 *      If any error occurs during the formatting process, it will return this instead. Defaults to '?'.
 * @returns {string}
 */
function displayNumberLocalizedAndWithSuffix(n, multiplierFactor, units='', maxDecimalPlaces=2, locale='en', errorRepresentation='?') {
    if (n >= (1000000000000 / multiplierFactor)) {
        return displayNumberLocalized(n / (1000000000000 / multiplierFactor), 'T' + units, maxDecimalPlaces,
            locale, errorRepresentation);
    }
    else if (n >= (1000000000 / multiplierFactor)) {
        return displayNumberLocalized(n / (1000000000 / multiplierFactor), 'G' + units, maxDecimalPlaces,
            locale, errorRepresentation);
    }
    else if (n >= (1000000 / multiplierFactor)) {
        return displayNumberLocalized(n / (1000000 / multiplierFactor), 'M' + units, maxDecimalPlaces,
            locale, errorRepresentation);
    }
    else if (n >= (1000 / multiplierFactor)) {
        return displayNumberLocalized(n / (1000 / multiplierFactor), 'k' + units, maxDecimalPlaces,
            locale, errorRepresentation);
    }
}
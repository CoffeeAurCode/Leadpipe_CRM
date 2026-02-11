// Helper: Format date with explicit UTC parsing
export function formatDate(dateString) {
    if (!dateString) return 'N/A';

    try {
        // Ensure the string has 'Z' suffix to explicitly mark it as UTC
        const utcString = dateString.endsWith('Z') ? dateString : dateString + 'Z';

        // parseISO will parse as UTC, and format will convert to local time
        return format(parseISO(utcString), 'MMM d, yyyy h:mm a');
    } catch (error) {
        console.error('Error formatting date:', error);
        return dateString;
    }
}

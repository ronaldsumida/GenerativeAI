let sessionID = "";

$(function() {
    $("#answer-button").click(async e => {
        e.preventDefault(); // Prevent postback

        // Get the question from the input field
        var question = $("#question")
        var query = question.val().trim();

        if (query.length > 0) {
            // Clear the output
            var answer = $("#answer");
            answer.text("");

            // Show the wait UI
            $("#overlay").css("display", "block");

            try {
                // Submit the question
                var response = await fetch('/streaming_chat', {
                    method: "POST"    ,
                    body: new URLSearchParams({ input: query }),
                    headers: {
                        "Content-Type": "application/x-www-form-urlencoded",
                        "X-Session-ID": sessionID
                    }
                });

                // Retrieve the session ID from the response
                sessionID = response.headers.get("X-Session-ID");

                // Hide the wait UI
                $("#overlay").css("display", "none");

                // Stream response and re-render markdown incrementally on each chunk
                var reader = response.body.getReader();
                var decoder = new TextDecoder("utf-8");
                var accumulatedText = "";

                while (true) {
                    var { done, value } = await reader.read();
                    if (done) break;
                    accumulatedText += decoder.decode(value, { stream: true });
                    answer.html(marked.parse(accumulatedText));
                }
            }
            catch (error) {
                // Let the user know that something went wrong
                answer.text("Error: " + error.message);
            }            
            finally {
                // Make sure the wait UI is hidden even if an exception occurs
                $("#overlay").css("display", "none");
            }
        }
    });
});
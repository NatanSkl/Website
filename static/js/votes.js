//TODO rewrite without copy paste

$(function() {
    $(".vote").click(function() {
        otherArrow = $(this).siblings(".vote");
        identifier = $(this).closest(".row").attr("identifier")
        if($(this).hasClass("glyphicon-arrow-up")) {
            if($(this).hasClass("upvoted")) {
                $(this).removeClass("upvoted")
                //Ajax to cancel upvotes
                $.post("/forums/vote", {
                    vote: "1",
                    isRemove: "true",
                    identifier: identifier
                }, function(data, status) {
                    if(status == "success") {
                        var votes = $("div[identifier=" + identifier + "]").find(".votes")
                        votes.text(parseInt(votes.text()) - 1)
                    }
                })
            }
            else {
                //Ajax to upvote
                voteNum = 1
                if(otherArrow.hasClass("downvoted")) {
                    otherArrow.removeClass("downvoted")
                    voteNum++
                }
                $(this).addClass("upvoted")
                $.post("/forums/vote", {
                    vote: "1",
                    isRemove: "false",
                    identifier: identifier
                }, function(data, status) {
                    if(status == "success") {
                        var votes = $("div[identifier=" + identifier + "]").find(".votes")
                        votes.text(parseInt(votes.text()) + voteNum)
                    }
                })
            }
        }
        if($(this).hasClass("glyphicon-arrow-down")) {
            if($(this).hasClass("downvoted")) {
                $(this).removeClass("downvoted")
                //Ajax to cancel downvote
                $.post("/forums/vote", {
                    vote: "-1",
                    isRemove: "true",
                    identifier: identifier
                }, function(data, status) {
                    if(status == "success") {
                        var votes = $("div[identifier=" + identifier + "]").find(".votes")
                        votes.text(parseInt(votes.text()) + 1)
                    }
                })
            }
            else {
                voteNum = 1
                if(otherArrow.hasClass("upvoted")) {
                    otherArrow.removeClass("upvoted")
                    voteNum++
                }
                $(this).addClass("downvoted")
                //Ajax to downvote
                $.post("/forums/vote", {
                    vote: "-1",
                    isRemove: "false",
                    identifier: identifier
                }, function(data, status) {
                    if(status == "success") {
                        var votes = $("div[identifier=" + identifier + "]").find(".votes")
                        votes.text(parseInt(votes.text()) - voteNum)
                    }
                })
            }
        }
    });
});
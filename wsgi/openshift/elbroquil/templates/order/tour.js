{% load i18n %}

tour = {
      id: "hello-hopscotch",
      i18n: {
        nextBtn: "{% trans 'Next' %}",
        prevBtn: "{% trans 'Previous' %}",
        doneBtn: "{% trans 'Done' %}",
        skipBtn: "{% trans 'Skip' %}",
        closeTooltip: "{% trans 'Close' %}",
        stepNums : ["1", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
      },
      steps: [
        {
          title: "{% trans 'Order Summary' %}",
          content: "{% trans 'Here you can see your order summary' %}",
          target: "order-summary",
          placement: "bottom"
        },
        {
          title: "{% trans 'No Order Yet' %}",
          content: "{% trans 'Your order summary would appear here' %}",
          target: "no-order-summary",
          placement: "bottom"
        },
        {
          title: "{% trans 'Make an Order' %}",
          content: "{% trans 'Click here to start making your order' %}",
          target: "make-order-button",
          placement: "left",
          multipage: true,
		  nextOnTargetClick: true,
          onNext: function() {
            window.location = "{% url 'elbroquil.views.update_order' order_first_page %}";
          }
        },
        {
          title: "{% trans 'Order a Product' %}",
          content: "{% trans 'Enter the amount of product you want here.' %}",
          target: document.querySelectorAll(".float-order")[0],
          placement: "bottom",
          zindex: 1000
        },
        {
          title: "{% trans 'Order a Product' %}",
          content: "{% trans 'Some products are ordered in units. You can use the up/down buttons to adjust the quantity you want.' %}",
          target: document.querySelectorAll(".integer-order")[0],
          placement: "bottom",
          zindex: 1000
        },
        {
          title: "{% trans 'Save the Changes' %}",
          content: "{% trans "When you make changes to your order, don't forget to save it!" %}",
          target: "#save_button",
          placement: "left",
  		  nextOnTargetClick: true,
          zindex: 1000
        },
        {
          title: "{% trans 'Browse by Categories' %}",
          content: "{% trans 'Here you can see the name of product category. Below, the order limit date for these products is shown. The color shows how much time you have left to update your order (green: much time, orange: one day, red: few hours).' %}",
          target: "h2.fillSpace",
          placement: "bottom",
          zindex: 1000
         },
        {
          title: "{% trans 'Browse by Categories' %}",
          content: "{% trans 'Click on these links to switch between product categories. You can also use the keyboard left and right arrow keys.' %}",
          target: document.querySelector(".next > a"),
          placement: "left",
          zindex: 1000,
    	  nextOnTargetClick: true,
          multipage: true,
          onNext: function() {
              window.location = "{% url 'elbroquil.views.update_order' order_last_page %}";
          }
         },
          {
            title: "{% trans 'View Your Order' %}",
            content: "{% trans 'When you are finished, check the order summary.' %}",
            target: document.querySelector(".next.importantlink > a"),
            placement: "left",
            zindex: 1000
          },
          {
              title: "{% trans 'View Your Order' %}",
              content: "{% trans 'You can also view your order from the top menu.' %}",
              target: "#order-total-dropdown",
              placement: "left",
              zindex: 1000
          }
      ]
    };




    exdays=60;
    var d = new Date();
    d.setTime(d.getTime() + (exdays*24*60*60*1000));
    var expires = "expires="+ d.toUTCString();
    document.cookie = "no_more_free_premium=1;" + expires + ";path=/;domain=."+domain;
    document.cookie = "no_more_promo_vc=1;" + expires + ";path=/;domain=."+domain;
    document.cookie = "no_more_push_premium=1;" + expires + ";path=/;domain=."+domain;
    document.cookie = "no_more_fraud_lightbox=1;" + expires + ";path=/;domain=."+domain;
    document.cookie = "no_more_free_premium=1;" + expires + ";path=/;domain=."+domain;






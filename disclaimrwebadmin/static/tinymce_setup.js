tinymce.init(
    {
        selector:'textarea#id_html',
        menubar: false,
        toolbar: "undo redo | styleselect fontselect fontsizeselect | bold italic | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | image | code",
        plugins: [
        	'image',
        	'code'
        ],
        font_formats:	"Arial=arial, helvetica, sans-serif;" +
        				"Arial Black=arial black, gadget, sans-serif;" +
        				"Courier New=courier new, courier, monospace;" +
        				"Comic Sans MS=comic sans ms, cursive, sans-serif;" +
        				"Georgia=georgia, serif;" +
        				"Impact=impact, charcoal, sans-serif;" +
        				"Lucidia Console=lucida console, monaco, monospace;" +
        				"Lucida Sans Unicode=lucidia sans unicode, lucida grande, sans-serif;" +
        				"Palatino Linotype=palatino linotype,book antiqua, palatino, serif;" +
        				"Tahoma=tahoma, geneva, sans-serif" +
        				"Times New Romain=times new roman, times, serif;" +
        				"Trebuchet MS=trebuchet ms, helvetica, sans-serif;" +
        				"Verdana=verdana, geneva, sans-serif"
        				
    }
);

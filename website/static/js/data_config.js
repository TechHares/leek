// trade_config_ajax.js
window.addEventListener("load", function () {
    (function ($) {
        $(document).ready(function () {
            function updateFields() {
                var traderClsValue = $('#id_data_cls').val();
                var csrftoken = $('[name=csrfmiddlewaretoken]').val();
                $.ajax({
                    url: '/admin/workstation/datasourceconfig/update_cls/',
                    type: 'POST',
                    data: {'data_cls': traderClsValue},
                    headers: {
                        'X-CSRFToken': csrftoken,
                    },
                    dataType: 'json',
                    success: function (data) {
                        // 根据返回的数据显示/隐藏相应的字段
                        data.fields_to_show.forEach(function (field) {
                            $('#id_' + field).closest('.form-row').show();
                        });

                        data.fields_to_hide.forEach(function (field) {
                            $('#id_' + field).closest('.form-row').hide();
                        });
                    },
                    error: function (error) {
                        console.error('Error updating fields:', error);
                    }
                });
            }

            // 调用 updateFields 在页面加载时执行一次
            updateFields();

            // 监听 trader_cls 字段的变化
            $('#id_data_cls').change(updateFields);
        });
    })(django.jQuery);
});


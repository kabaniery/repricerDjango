function ozon_loader() {
    fetch("{% url 'load_ozon'%}", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': "{{ csrf_token }}"
        },
    })
        .then(response => {
            if (!response.ok) {
                alert("�� ��� ��������� � �������");
            } else {
                alert("�������. �������� ������� ���������")
            }
        })
}
"""Tests for the low stock banner shown when the menu starts."""

import main


def test_banner_shows_number_of_low_stock_products(seeded_conn, capsys):
    main.show_low_stock_banner(seeded_conn)
    assert "2 products" in capsys.readouterr().out
